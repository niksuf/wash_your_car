import yaml


def read_yaml(filename):
    try:
        with open(filename) as file:
            data = yaml.load(file, Loader=yaml.CLoader)
        return data
    except FileNotFoundError:
        print(f'Config file {filename} not found!')
        exit()
