import os
from .autodock_basic import run_command, clear_tmp, retrieve_gcs_files, export_pose, add_protomers, prepare_receptor
from helpers_py.gcs_utils import download_from_gcs, upload_to_gcs

def prepare_reactive_ligand(lig_smiles: str, reactive_groups=None):
    print('Preparing reactive ligand...')
    output_path = '/tmp/lig_reactive'
    lig_with_protomers = add_protomers(lig_smiles)
    
    # Add reactive group parameters according to Meeko docs
    reactive_params = ''
    if reactive_groups:
        # Use --reactive parameter as per Meeko docs
        reactive_params = f"--reactive {','.join(reactive_groups)}"
    
    run_command(f'micromamba run -n dwa_env mk_prepare_ligand.py -i {lig_with_protomers} '
                f'--multimol_outdir {output_path} {reactive_params}')
    return f'{output_path}/_i0.pdbqt'

def run_reactive_docking(ligand_prepared: str, receptor_prepared: str, reactive_residues: str):
    print('Running reactive docking...')
    output_path = '/tmp/docking.pdbqt'
    config_txt = '/tmp/receptor_prepared.box.txt'
    
    # Format covalent residue parameter according to Meeko docs
    # Example format: 'CYS87:SG:1.8' (residue:atom:max_distance)
    residue_params = ''
    if reactive_residues:
        # Check if reactive_residues already has the correct format
        if ':' in reactive_residues:
            residue_params = f'--covalent {reactive_residues}'
        else:
            # Default to a standard format if only residue name/number is provided
            residue_params = f'--covalent {reactive_residues}:SG:2.0'
    
    run_command(f'micromamba run -n dwa_env vina --ligand {ligand_prepared} --receptor {receptor_prepared} --config {config_txt} --out {output_path} {residue_params}')
    return output_path

def run_job(ligand: str, receptor: str, box: str, dirname: str, reactive_groups=None, reactive_residues=None):
    try:
        clear_tmp()  # Clear temp files before running
        
        # Download necessary files from Cloud Storage
        remote_paths = [ligand, receptor, box]
        local_paths = retrieve_gcs_files(remote_paths)

        # Extract local paths for function calls
        ligand_local = local_paths[0]    # corresponds to ligand
        receptor_local = local_paths[1]  # corresponds to receptor
        box_local = local_paths[2]       # corresponds to box
        
        # Prepare ligand with reactive parameters
        ligand_prepared = prepare_reactive_ligand(ligand_local, reactive_groups)
        
        # Prepare receptor (same as basic docking)
        target, receptor_prepared = prepare_receptor(receptor_local, box_local)
        
        # Run reactive docking
        docking = run_reactive_docking(ligand_prepared, receptor_prepared, reactive_residues)
        
        # Export pose to SDF format
        pose = export_pose(docking)
        
        print('Uploading results to GCS...')
        # Upload files to GCS
        
        files_to_upload = [
            (docking, os.path.basename(docking)),
            (pose, os.path.basename(pose)),
            (target, os.path.basename(target)), # Used for visualization
        ]
        print(f'Files to upload: {files_to_upload}')
        
        # Upload files to GCS
        success_files = []
        failed_files = []

        # Upload files to GCS
        for local_path, blob_name in files_to_upload:
            if os.path.exists(local_path):
                if upload_to_gcs(local_path, dirname, blob_name):
                    success_files.append(blob_name)
                else:
                    failed_files.append(blob_name)
            else:
                print(f'File not found: {local_path}')
                failed_files.append(blob_name)
        
        print('Upload summary:')
        print(f'Successfully uploaded: {success_files}')
        print(f'Failed uploads: {failed_files}')
        
        if failed_files:
            return {'status': 'partial_success', 'uploaded_files': success_files, 'failed_files': failed_files}
        return {'status': 'success', 'uploaded_files': success_files} 
        
    except Exception as e:
        print(f'Error in reactive docking: {str(e)}')
        raise e
