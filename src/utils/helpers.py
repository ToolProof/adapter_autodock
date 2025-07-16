from helpers_py.gcs_utils import upload_to_gcs

def remove_ligand_from_complex(rec_raw):
    
    output_path = "/tmp/rec_no_lig.pdb"
    
    pymol_command = f"""
    micromamba run -n dwa_env pymol -qc -d "
    load {rec_raw};
    remove resn STI;
    save {output_path};
    quit
    "
    """
    run_command(pymol_command)
    print(f"Ligand removed: saved to {output_path}")
    return output_path