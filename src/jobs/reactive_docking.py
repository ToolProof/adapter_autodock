import os
from datetime import datetime
from .basic_docking import run_command, clear_tmp, retrieve_gcs_files, export_pose, add_protomers, prepare_receptor
from helpers_py.gcs_utils import download_from_gcs, upload_to_gcs

def prepare_reactive_ligand(lig_smiles, reactive_groups=None):
    print("Preparing reactive ligand...")
    output_path = "/tmp/lig_reactive"
    lig_with_protomers = add_protomers(lig_smiles)
    
    # Add reactive group parameters according to Meeko docs
    reactive_params = ""
    if reactive_groups:
        # Use --reactive parameter as per Meeko docs
        reactive_params = f"--reactive {','.join(reactive_groups)}"
    
    run_command(f"micromamba run -n dwa_env mk_prepare_ligand.py -i {lig_with_protomers} "
                f"--multimol_outdir {output_path} {reactive_params} --add_covalent_maps")
    return f"{output_path}/_i0.pdbqt"

def run_reactive_docking(lig_prepared, rec_prepared, reactive_residues):
    print("Running reactive docking...")
    output_path = "/tmp/lig_reactive_docking.pdbqt"
    config_txt = "/tmp/rec_prepared.box.txt"
    
    # Format covalent residue parameter according to Meeko docs
    # Example format: "CYS87:SG:1.8" (residue:atom:max_distance)
    residue_params = ""
    if reactive_residues:
        # Check if reactive_residues already has the correct format
        if ":" in reactive_residues:
            residue_params = f"--covalent {reactive_residues}"
        else:
            # Default to a standard format if only residue name/number is provided
            residue_params = f"--covalent {reactive_residues}:SG:2.0"
    
    run_command(f"micromamba run -n dwa_env vina --ligand {lig_prepared} --receptor {rec_prepared} "
                f"--config {config_txt} --out {output_path} {residue_params}")
    return output_path

def run_job(lig_name, lig_smiles_path, lig_box_path, rec_name, rec_no_lig_path, reactive_groups=None, reactive_residues=None):
    try:
        clear_tmp()  # Clear temp files before running
        
        # Download necessary files from Cloud Storage
        local_files = retrieve_gcs_files(
            lig_smiles_path=lig_smiles_path, 
            lig_box_path=lig_box_path, 
            rec_no_lig_path=rec_no_lig_path
        )

        # Extract local paths for function calls
        lig_smiles = local_files["lig_smiles"]
        lig_box = local_files["lig_box"]
        rec_no_lig = local_files["rec_no_lig"]
        
        # Prepare ligand with reactive parameters
        lig_prepared = prepare_reactive_ligand(lig_smiles, reactive_groups)
        
        # Prepare receptor (same as basic docking)
        rec_prepared = prepare_receptor(rec_no_lig, lig_box)
        
        # Run reactive docking
        lig_docking = run_reactive_docking(lig_prepared, rec_prepared, reactive_residues)
        
        # Export pose to SDF format
        lig_pose = export_pose(lig_docking)
        
        # Get the current date and time
        now = datetime.now()
        # Format the date and time as a string
        date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Ensure the directory exists
        os.makedirs(date_time_str, exist_ok=True)
        
        files_to_upload = [
            (lig_docking, f"reactive/{date_time_str}{lig_docking[4:]}"),
            (lig_pose, f"reactive/{date_time_str}{lig_pose[4:]}")
        ]
        
        # Upload files to GCS
        success_files = []
        failed_files = []
        bucket_name = "tp_resources"

        # Upload files to GCS
        for local_path, blob_name in files_to_upload:
            if os.path.exists(local_path):
                if upload_to_gcs(local_path, bucket_name, blob_name):
                    success_files.append(blob_name)
                else:
                    failed_files.append(blob_name)
            else:
                print(f"File not found: {local_path}")
                failed_files.append(blob_name)
        
        print("Upload summary:")
        print(f"Successfully uploaded: {success_files}")
        print(f"Failed uploads: {failed_files}")
        
        if failed_files:
            return {"status": "partial_success", "uploaded_files": success_files, "failed_files": failed_files}
        return {"status": "success", "uploaded_files": success_files} 
        
    except Exception as e:
        print(f"Error in reactive docking: {str(e)}")
        raise e
