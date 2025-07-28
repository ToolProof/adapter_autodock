'''
Docstring
'''
from flask import Flask, request, jsonify
from src.jobs import basic_docking
from src.jobs import reactive_docking

app = Flask(__name__) 

@app.route('/basic_docking', methods=['GET', 'POST'])
def basic_docking_endpoint():
    '''
    Docstring
    '''
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON payload provided'}), 400
       
        try:
            # Extract arguments from JSON payload
            ligand = data.get('ligand')
            receptor = data.get('receptor')
            box = data.get('box')
            
            dirname = 'adapter_autodock/basic_docking/' # ATTENTION
            
            # Log the extracted values
            # print(f'Ligand: {ligand}, Receptor: {receptor}, Box: {box}')

            # Run the basic_docking job
            result = basic_docking.run_job(ligand, receptor, box, dirname)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'Basic docking endpoint'})


@app.route('/reactive_docking', methods=['GET', 'POST'])
def reactive_docking_endpoint():
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON payload provided'}), 400

        data = request.get_json()
        
        try:
            # Extract arguments from JSON payload
            ligand = data.get('candidate')
            receptor = data.get('target')
            box = data.get('box')
            dirname = data.get('outputDir')
            reactive_groups = data.get('reactive_groups', None)
            reactive_residues = data.get('reactive_residues', None)

            # Call the workflow from reactive_docking
            result = reactive_docking.run_job(
                ligand, 
                receptor, 
                box, 
                dirname,
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