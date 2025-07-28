'''
Docstring
'''
import os
from typing import Dict, List, Union
from datetime import datetime
from helpers_py.gcs_utils import upload_to_gcs
from helpers_py.os_utils import run_command, clear_tmp
from src.helpers.autodock_utils import add_protomers, prepare_receptor, export_pose, retrieve_gcs_files


def prepare_ligand(ligand: str) -> str:
    '''
    Prepares the ligand for docking by generating its protomers.
    '''
    print('Preparing ligand...')
    output_path = '/tmp/ligand_protomers'
    ligand_with_protomers = add_protomers(ligand)
    run_command(f'micromamba run -n adapter_autodock_env mk_prepare_ligand.py -i {ligand_with_protomers} --multimol_outdir {output_path}')
    return f'{output_path}/_i0.pdbqt' # ATTENTION: hack since output_path is a directory
    

def run_docking(ligand_prepared: str, receptor_prepared: str) -> str:
    '''
    Runs the docking simulation using Vina.
    '''
    print('Running docking...')
    output_path = '/tmp/docking.pdbqt'
    config_txt = '/tmp/receptor_prepared.box.txt' # ATTENTION
    run_command(f'micromamba run -n adapter_autodock_env vina --ligand {ligand_prepared} --receptor {receptor_prepared} --config {config_txt} --out {output_path}')
    return output_path


def run_job(ligand: str, receptor: str, box: str, dirname: str) -> Dict[str, Union[Dict[str, Union[str, None]], Dict[str, Union[str, List[str]]]]]:
    '''
    Docstring
    '''
    try:
        clear_tmp()  # Clear temp files before running
        
        # Download necessary files from Cloud Storage
        remote_paths = [ligand, receptor, box]
        local_paths = retrieve_gcs_files(remote_paths)

        # Extract local paths for function calls
        ligand_local = local_paths[0]    # corresponds to ligand
        receptor_local = local_paths[1]  # corresponds to receptor
        box_local = local_paths[2]       # corresponds to box
        
        ligand_prepared = prepare_ligand(ligand_local)
        
        receptor_visualization, receptor_prepared = prepare_receptor(receptor_local, box_local)
        
        ligand_docking = run_docking(ligand_prepared, receptor_prepared)
        
        ligand_pose = export_pose(ligand_docking) 
        
        # Upload files to GCS
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        files_to_upload = [
            (ligand_docking, f"{dirname}ligand_docking/", f"{timestamp}.pdbqt", "ligand_docking"),
            (ligand_pose, f"{dirname}ligand_pose/", f"{timestamp}.sdf", "ligand_pose"),
            (receptor_visualization, f"{dirname}receptor_visualization/", f"{timestamp}.pdb", "receptor_visualization"),
        ]
        
        success_files: Dict[str, str] = {}
        failed_files: List[str] = []

        # Upload files to GCS
        for local_path, upload_dir, filename, file_type in files_to_upload:
            if os.path.exists(local_path):
                if upload_to_gcs(local_path, upload_dir, filename):
                    success_files[file_type] = filename
                else:
                    failed_files.append(filename)
            else:
                print(f'File not found: {local_path}')
                failed_files.append(filename)
        
        print('Upload summary:')
        print(f'Successfully uploaded: {list(success_files.values())}')
        print(f'Failed uploads: {failed_files}')

        if failed_files:
            return {
                'outputs': {
                    'ligand_docking': success_files.get('ligand_docking'),
                    'ligand_pose': success_files.get('ligand_pose'),
                    'receptor_visualization': success_files.get('receptor_visualization')
                },
                'metadata': {
                    'status': 'partial_success',
                    'failed_files': failed_files
                }
            }
        return {
            'outputs': {
                'ligand_docking': success_files['ligand_docking'],
                'ligand_pose': success_files['ligand_pose'],
                'receptor_visualization': success_files['receptor_visualization']
            },
            'metadata': {
                'status': 'success'
            }
        } 
    except Exception as e:
        raise RuntimeError(f'Workflow failed: {e}')