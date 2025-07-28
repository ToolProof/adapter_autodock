'''
Docstring
'''
from flask import Flask, request, jsonify
from src.jobs import autodock_basic
from src.jobs import autodock_reactive

app = Flask(__name__) 

@app.route('/adapter_autodock_basic', methods=['GET', 'POST'])
def adapter_autodock_basic():
    '''
    Docstring
    '''
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON payload provided'}), 400
       
        try:
            # Extract arguments from JSON payload
            ligand = data.get('candidate')
            receptor = data.get('target')
            box = data.get('box')
            dirname = data.get('outputDir')
            
            # Log the extracted values
            print(f'Ligand: {ligand}, Receptor: {receptor}, Box: {box}')

            # Call the workflow from basic_docking
            result = autodock_basic.run_job(ligand, receptor, box, dirname)
            return jsonify({'message': 'Automation completed successfully', 'result': result}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'Basic docking endpoint'})


@app.route('/adapter_autodock_reactive', methods=['GET', 'POST'])
def adapterautodock_reactive():
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON payload provided'}), 400

        data = request.get_json()
        
        try:
            # Extract arguments from JSON payload
            lig_name = data.get('lig_name')
            lig_smiles_path = data.get('lig_smiles_path')
            lig_box_path = data.get('lig_box_path')
            rec_name = data.get('rec_name')
            rec_no_lig_path = data.get('rec_no_lig_path')
            reactive_groups = data.get('reactive_groups', None)
            reactive_residues = data.get('reactive_residues', None)

            # Call the workflow from reactive_docking
            result = autodock_reactive.run_job(
                lig_name, 
                lig_smiles_path, 
                lig_box_path, 
                rec_name, 
                rec_no_lig_path,
                reactive_groups,
                reactive_residues
            )
            return jsonify({'message': 'Reactive docking completed successfully', 'result': result}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    return jsonify({'message': 'Reactive docking endpoint'})

if __name__ == '__main__':
    # Expose the app on port 8080
    app.run(host='0.0.0.0', port=8080, debug=True)