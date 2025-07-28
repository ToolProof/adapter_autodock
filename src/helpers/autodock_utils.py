import os
from typing import List
from helpers_py.gcs_utils import download_from_gcs
from helpers_py.os_utils import run_command


def add_protomers(ligand: str) -> str:
    '''
    Prepares the ligand by generating its protomers.
    '''
    output_path = '/tmp/ligand_with_protomers.sdf'
    
    # Read the SMILES string from the file
    try:
        with open(ligand, 'r', encoding='utf-8') as file:
            smiles_string = file.read().strip()
    except Exception as e:
        raise RuntimeError(f'Failed to read SMILES file {ligand}: {e}') from e

    # Run the command with the SMILES string
    run_command(f'micromamba run -n adapter_autodock_env scrub.py "{smiles_string}" -o {output_path} --skip_tautomers --ph_low 5 --ph_high 9')
    
    return output_path


def prepare_receptor(receptor: str, box: str) -> tuple[str, str]:
    '''
    Docstring
    '''
    print('Preparing receptor...')
    intermediate_path = '/tmp/receptor_prepared'
    output_path = f'{intermediate_path}.pdbqt' # ATTENTION

    # Step 1: Extract receptor atoms
    receptor_atoms = extract_receptor_atoms(receptor)
    
    # Step 2: Combine CRYST1 and receptor atoms
    receptor_cryst1 = extract_and_combine_cryst1(receptor, receptor_atoms)
    print(f'CRYST1 combined: saved to {receptor_cryst1}')

    # Step 3: Add hydrogens and optimize
    receptor_cryst1FH = add_hydrogens_and_optimize(receptor_cryst1)
    print(f'Hydrogens added and optimized: saved to {receptor_cryst1FH}')

    # Step 4: Prepare receptor for docking
    run_command(f'micromamba run -n adapter_autodock_env mk_prepare_receptor.py --read_pdb {receptor_cryst1FH} -o {intermediate_path} -p -v --box_enveloping {box} --padding 5')
    print('Receptor preparation complete.')
    return receptor_cryst1FH, output_path


def extract_receptor_atoms(receptor: str) -> str:
    '''
    Extracts the receptor atoms from the PDB file.
    '''
    output_path = '/tmp/receptor_atoms.pdb'
    run_command(f'''micromamba run -n adapter_autodock_env python3 - <<EOF
from prody import parsePDB, writePDB
pdb_token = '{receptor}'
atoms_from_pdb = parsePDB(pdb_token)
receptor_selection = 'chain A and not water and not hetero'
receptor_atoms = atoms_from_pdb.select(receptor_selection)
writePDB('{output_path}', receptor_atoms)
EOF
''')
    print(f'Receptor atoms extracted: saved to {output_path}')
    return output_path


def extract_and_combine_cryst1(receptor: str, receptor_atoms: str) -> str:
    '''
    Extracts the CRYST1 information from the receptor PDB file and combines it with the receptor atoms.
    '''
    print('Extracting CRYST1 and combining with receptor atoms...')
    output_path = '/tmp/receptor_cryst1.pdb'
    cryst1_line = run_command(f'grep "CRYST1" {receptor}', check=False).stdout.strip()
    with open(receptor_atoms, 'r', encoding='utf-8') as receptor_f, open(output_path, 'w', encoding='utf-8') as combined_f:
        if cryst1_line:
            combined_f.write(cryst1_line + '\n')
        combined_f.writelines(receptor_f.readlines())
    print('Combined receptor file created: {output_path}')
    return output_path


def add_hydrogens_and_optimize(receptor_cryst1: str) -> str:
    '''
    Adds hydrogens to the receptor and optimizes the structure.
    '''
    print('Adding hydrogens and optimizing with reduce2.py...')
    output_path = '/tmp/receptor_cryst1FH.pdb' # ATTENTION
    # Find the path to the reduce2.py script within the micromamba environment (adapter_autodock_env)
    micromamba_path = '/opt/conda/envs/adapter_autodock_env/lib/python3.11/site-packages'
    reduce2_path = os.path.join(micromamba_path, 'mmtbx', 'command_line', 'reduce2.py')
    reduce_opts = 'approach=add add_flip_movers=True'

    # Set up the geostd path
    geostd_path = os.path.abspath('geostd')
    env = os.environ.copy()
    env['MMTBX_CCP4_MONOMER_LIB'] = geostd_path
    
    # Save the current working directory to return to it later
    current_dir = os.getcwd()
    
    # Change the working directory to /tmp/
    os.chdir('/tmp/')

    # Run reduce2.py within the micromamba environment
    run_command(
        f'micromamba run -n adapter_autodock_env python3 {reduce2_path} {receptor_cryst1} {reduce_opts}', 
        env=env
    )
    
    # Change the working directory back to the original one
    os.chdir(current_dir)
    
    print('Hydrogens added and optimized. Output: {output_path}')
    
    return output_path


def remove_ligand_from_complex(rec_raw: str) -> str:
    
    output_path = "/tmp/rec_no_lig.pdb"
    
    pymol_command = f"""
    micromamba run -n adapter_autodock_env pymol -qc -d "
    load {rec_raw};
    remove resn STI;
    save {output_path};
    quit
    "
    """
    run_command(pymol_command)
    print(f"Ligand removed: saved to {output_path}")
    return output_path


def export_pose(docking: str) -> str:
    '''
    Exports the docked pose to a SDF file.
    '''
    print('Exporting docked pose...')
    output_path = '/tmp/pose.sdf'
    run_command(f'micromamba run -n adapter_autodock_env mk_export.py {docking} -s {output_path}')
    return output_path


def retrieve_gcs_files(remote_paths: List[str]) -> List[str]:
    '''
    Retrieves files from Cloud Storage and stores them in /tmp.
    Returns a list of local file paths corresponding to the input remote paths.
    '''
    local_files: List[str] = []
    
    for gcs_path in remote_paths:
        local_path: str = download_from_gcs(gcs_path)
        local_files.append(local_path)
            
    
    return local_files