import glob
import os
import sys

import aiida_lammps.tests.utils as tests
import numpy as np
import pytest


def eam_data():
    cell = [[2.848116, 0.000000, 0.000000],
            [0.000000, 2.848116, 0.000000],
            [0.000000, 0.000000, 2.848116]]

    scaled_positions = [(0.0000000, 0.0000000, 0.0000000),
                        (0.5000000, 0.5000000, 0.5000000)]

    symbols = ['Fe', 'Fe']

    struct_dict = {"cell": cell,
                   "symbols": symbols,
                   "scaled_positions": scaled_positions}

    eam_path = os.path.join(tests.TEST_DIR, 'input_files', 'Fe_mm.eam.fs')
    eam_data = {'type': 'fs',
                'file_contents': open(eam_path).readlines()}

    potential_dict = {'pair_style': 'eam', 'data': eam_data}

    output_dict = {"energy": -8.2448702,
                   "infiles": ['input.data', 'input.in', 'potential.pot']}

    return struct_dict, potential_dict, output_dict


def lj_data():
    cell = [[3.987594, 0.000000, 0.000000],
            [-1.993797, 3.453358, 0.000000],
            [0.000000, 0.000000, 6.538394]]

    symbols = ['Ar'] * 2
    scaled_positions = [(0.33333, 0.66666, 0.25000),
                        (0.66667, 0.33333, 0.75000)]

    struct_dict = {"cell": cell,
                   "symbols": symbols,
                   "scaled_positions": scaled_positions}

    # Example LJ parameters for Argon. These may not be accurate at all
    potential_dict = {
        'pair_style': 'lennard_jones',
        #                 epsilon,  sigma, cutoff
        'data': {'1  1': '0.01029   3.4    2.5',
                 # '2  2':   '1.0      1.0    2.5',
                 # '1  2':   '1.0      1.0    2.5'
                 }
    }

    output_dict = {"energy": 0.0,  # TODO should LJ energy be be 0?
                   "infiles": ['input.data', 'input.in']}

    return struct_dict, potential_dict, output_dict


def tersoff_data():
    cell = [[3.1900000572, 0, 0],
            [-1.5950000286, 2.762621076, 0],
            [0.0, 0, 5.1890001297]]

    scaled_positions = [(0.6666669, 0.3333334, 0.0000000),
                        (0.3333331, 0.6666663, 0.5000000),
                        (0.6666669, 0.3333334, 0.3750000),
                        (0.3333331, 0.6666663, 0.8750000)]

    symbols = ['Ga', 'Ga', 'N', 'N']

    struct_dict = {"cell": cell,
                   "symbols": symbols,
                   "scaled_positions": scaled_positions}

    tersoff_gan = {
        'Ga Ga Ga': '1.0 0.007874 1.846 1.918000 0.75000 -0.301300 1.0 1.0 1.44970 410.132 2.87 0.15 1.60916 535.199',
        'N  N  N': '1.0 0.766120 0.000 0.178493 0.20172 -0.045238 1.0 1.0 2.38426 423.769 2.20 0.20 3.55779 1044.77',
        'Ga Ga N': '1.0 0.001632 0.000 65.20700 2.82100 -0.518000 1.0 0.0 0.00000 0.00000 2.90 0.20 0.00000 0.00000',
        'Ga N  N': '1.0 0.001632 0.000 65.20700 2.82100 -0.518000 1.0 1.0 2.63906 3864.27 2.90 0.20 2.93516 6136.44',
        'N  Ga Ga': '1.0 0.001632 0.000 65.20700 2.82100 -0.518000 1.0 1.0 2.63906 3864.27 2.90 0.20 2.93516 6136.44',
        'N  Ga N ': '1.0 0.766120 0.000 0.178493 0.20172 -0.045238 1.0 0.0 0.00000 0.00000 2.20 0.20 0.00000 0.00000',
        'N  N  Ga': '1.0 0.001632 0.000 65.20700 2.82100 -0.518000 1.0 0.0 0.00000 0.00000 2.90 0.20 0.00000 0.00000',
        'Ga N  Ga': '1.0 0.007874 1.846 1.918000 0.75000 -0.301300 1.0 0.0 0.00000 0.00000 2.87 0.15 0.00000 0.00000'}

    potential_dict = {'pair_style': 'tersoff',
                      'data': tersoff_gan}

    output_dict = {"energy": -18.11122,
                   "infiles": ['input.data', 'input.in', 'potential.pot']}

    return struct_dict, potential_dict, output_dict


def optimisation_calc(workdir, configure, struct_dict, potential_dict):
    from aiida.orm import DataFactory
    StructureData = DataFactory('structure')
    ParameterData = DataFactory('parameter')

    computer = tests.get_computer(workdir=workdir, configure=configure)

    structure = StructureData(cell=struct_dict["cell"])

    for scaled_position, symbols in zip(struct_dict["scaled_positions"], struct_dict["symbols"]):
        structure.append_atom(position=np.dot(scaled_position, struct_dict["cell"]).tolist(),
                              symbols=symbols)

    potential = ParameterData(dict=potential_dict)

    parameters_opt = {
        'lammps_version': tests.lammps_version(),
        'relaxation': 'tri',  # iso/aniso/tri
        'pressure': 0.0,  # kbars
        'vmax': 0.000001,  # Angstrom^3
        'energy_tolerance': 1.0e-25,  # eV
        'force_tolerance': 1.0e-25,  # eV angstrom
        'max_evaluations': 1000000,
        'max_iterations': 500000}
    parameters = ParameterData(dict=parameters_opt)

    from aiida.orm import Code
    code = Code(
        input_plugin_name='lammps.optimize',
        remote_computer_exec=[computer, tests.get_path_to_executable(tests.TEST_EXECUTABLE)],
    )
    code.store()

    calc = code.new_calc()
    calc.set_withmpi(False)
    calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 1})

    calc.label = "test lammps calculation"
    calc.description = "A much longer description"
    calc.use_structure(structure)
    calc.use_potential(potential)

    calc.use_parameters(parameters)

    input_dict = {
        "options": {
            "resources": {
                "num_machines": 1,
                "num_mpiprocs_per_machine": 1
            },
            "withmpi": False,
            "max_wallclock_seconds": 60
        },
        "structure": structure,
        "potential": potential,
        "parameters": parameters,
        "code": code
    }

    return calc, input_dict


@pytest.mark.parametrize('data_func', [
    eam_data,
    lj_data,
    tersoff_data,
])
def test_opt_submission(new_database, new_workdir, data_func):
    struct_dict, potential_dict, output_dict = data_func()

    calc, input_dict = optimisation_calc(new_workdir, False, struct_dict, potential_dict)

    from aiida.common.folders import SandboxFolder

    # output input files and scripts to temporary folder
    with SandboxFolder() as folder:
        subfolder, script_filename = calc.submit_test(folder=folder)
        print("inputs created successfully at {}".format(subfolder.abspath))
        print([
            os.path.basename(p)
            for p in glob.glob(os.path.join(subfolder.abspath, "*"))
        ])
        for infile in output_dict['infiles']:
            assert subfolder.isfile(infile)


@pytest.mark.lammps_call
@pytest.mark.timeout(120)
@pytest.mark.skipif(
    tests.aiida_version() < tests.cmp_version('1.0.0a1') and tests.is_sqla_backend(),
    reason='Error in obtaining authinfo for computer configuration')
@pytest.mark.parametrize('data_func', [
    eam_data,
    lj_data,
    tersoff_data
])
def test_opt_process(new_database_with_daemon, new_workdir, data_func):
    struct_dict, potential_dict, output_dict = data_func()

    calc, input_dict = optimisation_calc(new_workdir, True, struct_dict, potential_dict)

    process = calc.process()

    calcnode = tests.run_get_node(process, input_dict)

    sys.stdout.write(tests.get_calc_log(calcnode))

    print(calcnode.get_inputs_dict())
    assert set(calcnode.get_inputs_dict().keys()).issuperset(
        ['parameters', 'structure', 'potential'])

    print(calcnode.get_outputs_dict())
    assert set(calcnode.get_outputs_dict().keys()).issuperset(
        ['output_parameters', 'output_array', 'output_structure'])

    from aiida.common.datastructures import calc_states
    assert calcnode.get_state() == calc_states.FINISHED

    pdict = calcnode.out.output_parameters.get_dict()
    assert set(pdict.keys()).issuperset(['energy', 'warnings', 'energy_units', 'force_units'])
    assert pdict['warnings'] == []
    assert pdict['energy'] == pytest.approx(output_dict['energy'])

    assert set(calcnode.out.output_array.get_arraynames()).issuperset(
        ['stress', 'forces']
    )
