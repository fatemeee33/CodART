import csv


class CandidateReader:
    def __init__(self, path: str):
        csv_file = open(path, newline='')
        data = csv.reader(csv_file)
        self.data = []
        for row in data:
            self.data.append(row)

    def get_conf(self, index: int):
        _conf = {
            'target_file': self.data[index][0],
            'lines': [int(x) for x in str(self.data[index][2]).split('::')],
        }
        return _conf

    def __len__(self):
        return len(self.data)


if __name__ == '__main__':
    _addr = '/mnt/d/Sajad/Uni/Spring00/Compiler/CodART/tests/extract_method/benchmark_projects_test/JSON/Long-Method.csv'
    cr = CandidateReader(_addr)
    print(cr.get_conf(0))
