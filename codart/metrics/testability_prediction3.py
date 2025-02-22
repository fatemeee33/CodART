"""

This module contains light-weight version of testability prediction script (with 10 metrics)
The top 10 metrics are selected based on the permutation importance scoring techniques.
to be used in refactoring process in addition to QMOOD metrics.

"""

__version__ = '0.1.2'
__author__ = 'Morteza Zakeri'

import os
import pandas as pd
import joblib

import understand as und

from codart import config

scaler1 = joblib.load(os.path.join(os.path.dirname(__file__), 'data_model/DS07710.joblib'))
model5 = joblib.load(os.path.join(os.path.dirname(__file__), 'sklearn_models7/VR1_DS7.joblib'))

condition_kw_list = ['if', 'for', 'while', 'switch', '?', 'assert', ]


class TestabilityPredicator:
    def __init__(self, db_path):
        self.scaler = scaler1
        self.model = model5
        self.db_path = db_path
        self.df_all = pd.DataFrame()

    def prepare_metric_dataframe(self):
        dbx = und.open(self.db_path)
        kind_filter = 'Java Class ~TypeVariable ~Anonymous ~Enum ~Unknown ~Unresolved ~Jar ~Library, Java Interface'
        class_entities = dbx.ents(kind_filter)
        for class_entity in class_entities:
            # print (class_entity.kind().name())

            # Compute method-level metrics
            # method_list = class_entity.ents('Define', 'Java Method ~Unknown ~Unresolved ~Jar ~Library')
            number_of_local_methods_all = class_entity.metric(['CountDeclMethodAll'])['CountDeclMethodAll']
            number_of_local_methods = class_entity.metric(['CountDeclMethod'])['CountDeclMethod']
            if number_of_local_methods is None or number_of_local_methods == 0:
                avg_loc_exe = 0
                avg_loc = 0
                avg_statement_decl = 0
                nim = number_of_local_methods_all
            else:
                avg_loc_exe = class_entity.metric(['CountLineCodeExe'])['CountLineCodeExe'] / number_of_local_methods
                avg_loc = class_entity.metric(['CountLineCode'])['CountLineCode'] / number_of_local_methods
                avg_statement_decl = class_entity.metric(['CountLineCodeDecl'])[
                                         'CountLineCodeDecl'] / number_of_local_methods
                nim = number_of_local_methods_all - number_of_local_methods

            # Compute lexical metrics
            identifiers_list = list()
            condition_count = 0
            dots_count = 0
            lexeme_ = class_entity.lexer(show_inactive=False).first()
            while lexeme_ is not None:
                if lexeme_.token() == 'Identifier':
                    identifiers_list.append(lexeme_.text())
                elif lexeme_.text() in condition_kw_list:
                    condition_count += 1
                elif lexeme_.text() == '.':
                    dots_count += 1
                lexeme_ = lexeme_.next()

            dfx = pd.DataFrame()
            dfx['Class'] = [class_entity.longname()]
            dfx['CSORD_AvgLineCodeExe'] = [avg_loc_exe]
            dfx['CSLEX_NumberOfConditionalJumpStatements'] = [condition_count]
            dfx['CSORD_AvgLineCode'] = [avg_loc]
            dfx['CSORD_NumberOfDepends'] = [len(class_entity.depends())]
            dfx['CSLEX_NumberOfUniqueIdentifiers'] = [len(set(identifiers_list))]
            dfx['CSLEX_NumberOfDots'] = [dots_count]  # 6
            dfx['CSORD_CountDeclInstanceMethod'] = [
                class_entity.metric(['CountDeclInstanceMethod'])['CountDeclInstanceMethod']]  # 7
            dfx['CSORD_CountDeclMethodPublic'] = [
                class_entity.metric(['CountDeclMethodPublic'])['CountDeclMethodPublic']]  # 8
            dfx['CSORD_NIM'] = [nim]  # 9
            dfx['CSORD_AvgStmtDecl'] = [avg_statement_decl]  # 10

            self.df_all = pd.concat([self.df_all, dfx], ignore_index=True)

        dbx.close()

    def inference(self, verbose=False, log_path=None):
        self.df_all = self.df_all.fillna(0)
        X_test1 = self.df_all.iloc[:, 1:]
        X_test = self.scaler.transform(X_test1)
        y_pred = self.model.predict(X_test)
        df_new = pd.DataFrame(self.df_all.iloc[:, 0], columns=['Class'])
        df_new['PredictedTestability'] = list(y_pred)

        if verbose:
            self.export_class_testability_values(df=df_new, log_path=log_path)
        return df_new['PredictedTestability'].sum()  # Return sum instead mean

    @classmethod
    def export_class_testability_values(cls, df=None, log_path=None):
        if log_path is None:
            log_path = os.path.join(
                config.PROJECT_LOG_DIR,
                f'classes_testability2_for_problem_{config.PROBLEM}.csv')
        config.logger.info(log_path)
        config.logger.info(f'count classes testability2\t {df["PredictedTestability"].count()}')
        config.logger.info(f'minimum testability2\t {df["PredictedTestability"].min()}')
        config.logger.info(f'maximum testability2\t {df["PredictedTestability"].max()}')
        config.logger.info(f'variance testability2\t {df["PredictedTestability"].var()}')
        config.logger.info(f'sum classes testability2\t, {df["PredictedTestability"].sum()}')
        config.logger.info('-' * 50)

        df.to_csv(log_path, index=False)


def main(db_path, initial_value=1.0, verbose=False, log_path=None):
    testability_ = TestabilityPredicator(db_path=db_path)
    testability_.prepare_metric_dataframe()
    return testability_.inference(verbose=verbose, log_path=log_path) / initial_value


# Test module
if __name__ == '__main__':
    print(f"UDB path: {config.UDB_PATH}")
    for i in range(0, 1):
        print(main(config.UDB_PATH, initial_value=1.0, verbose=False))
