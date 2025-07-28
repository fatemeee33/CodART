"""
## Introduction

Although it was planned to use a field universally for all classes, in reality the field is used only in
some subclasses. This situation can occur when planned features fail to pan out, for example.
because of this, we push down the field from the superclass into its related subclass.

## Pre and Post Conditions

### Pre Conditions:
1. There should exist a corresponding child and parent in the project.

2. The field that should be pushed down must be valid.

3. The user must enter the package's name, class's name and the fields that need to be added.

### Post Conditions:
1. The changed field's usages and callings will also change respectively.

2. There will be children and parents having their desired fields added or removed.
"""

__version__ = '0.1.1'
__author__ = 'Morteza Zakeri'

from codart import symbol_table
from codart.config import logger


class PushDownField:
    """

    The main function that does the process of pull up field refactoring.

    Adds the necessary fields to the subclasses and removes them from the superclass.

    """

    def __init__(self, source_filenames: list,
                 package_name: str,
                 superclass_name: str,
                 field_name: str,
                 class_names: list = [],
                 filename_mapping=lambda x: (x[:-5] if x.endswith(".java") else x) + ".java"):
        """

        Args:

            source_filenames (list): A list of file names to be processed

            package_name (str): The name of the package in which the refactoring has to be done \
            (contains the superclass)

            superclass_name (str): The name of the needed superclass

            class_names (list): Name of the classes in which the refactoring has to be done \
            (the classes to push down field from)

            field_name (str): Name of the field that has to be refactored

            filename_mapping (str): Mapping the file's name to the correct format so that it can be processed

        Returns:

            object (PushDownField): An instance of PushDownField class

        """
        self.source_filenames = source_filenames
        self.package_name = package_name
        self.superclass_name = superclass_name
        self.field_name = field_name
        self.class_names = class_names
        self.filename_mapping = filename_mapping

    def pre_condition_check(self, program, superclass):
        if self.package_name not in program.packages \
                or self.superclass_name not in program.packages[self.package_name].classes \
                or self.field_name not in program.packages[self.package_name].classes[self.superclass_name].fields:
            return False

        for m in superclass.methods:
            method: symbol_table.Method = superclass.methods[m]
            for item in method.body_local_vars_and_expr_names:
                if isinstance(item, symbol_table.ExpressionName):
                    if ((len(item.dot_separated_identifiers) == 1
                         and item.dot_separated_identifiers[0] == self.field_name)
                            or (len(item.dot_separated_identifiers) == 2
                                and item.dot_separated_identifiers[0] == "this"
                                and item.dot_separated_identifiers[1] == self.field_name)):
                        return False
        return True

    def do_refactor(self):
        program = symbol_table.get_program(self.source_filenames, print_status=False)
        superclass: symbol_table.Class = program.packages[self.package_name].classes[self.superclass_name]
        if not self.pre_condition_check(program, superclass):
            print(f"Cannot push-down field from {superclass.name}")
            return False

        other_derived_classes = []
        classes_to_add_to = []
        for pn in program.packages:
            p: symbol_table.Package = program.packages[pn]
            for cn in p.classes:
                c: symbol_table.Class = p.classes[cn]
                if ((c.superclass_name == self.superclass_name and
                     c.file_info.has_imported_class(self.package_name, self.superclass_name)) or
                        (
                                self.package_name is not None and c.superclass_name == self.package_name + '.' + self.superclass_name)):
                    # all_derived_classes.append(c)
                    if len(self.class_names) == 0 or cn in self.class_names:
                        if self.field_name in c.fields:
                            print("some classes have same variable")
                            return False
                        else:
                            classes_to_add_to.append(c)
                    else:
                        other_derived_classes.append(c)

        # Check if the field is used from the superclass or other derived classes
        for pn in program.packages:
            p: symbol_table.Package = program.packages[pn]
            for cn in p.classes:
                c: symbol_table.Class = p.classes[cn]
                has_imported_superclass = c.file_info.has_imported_class(self.package_name, self.superclass_name)
                fields_of_superclass_type_or_others = []
                for fn in c.fields:
                    f: symbol_table.Field = c.fields[fn]
                    if (f.name == self.field_name and has_imported_superclass) \
                            or (self.package_name is not None and f.name == (
                            self.package_name + '.' + self.superclass_name)):
                        fields_of_superclass_type_or_others.append(f.name)
                    if any((c.file_info.has_imported_class(o.package_name, o.name) and f.datatype == o.name)
                           or f.datatype == (o.package_name + '.' + o.name) for o in other_derived_classes):
                        fields_of_superclass_type_or_others.append(f.name)
                for mk in c.methods:
                    m: symbol_table.Method = c.methods[mk]
                    local_vars_of_superclass_type_or_others = []
                    for item in m.body_local_vars_and_expr_names:
                        if isinstance(item, symbol_table.LocalVariable):
                            if (item.datatype == self.superclass_name and has_imported_superclass) \
                                    or item.datatype == (self.package_name + '.' + self.superclass_name):
                                local_vars_of_superclass_type_or_others.append(item.identifier)
                            if any((c.file_info.has_imported_class(o.package_name, o.name) and item.datatype == o.name)
                                   or item.datatype == (o.package_name + '.' + o.name) for o in other_derived_classes):
                                local_vars_of_superclass_type_or_others.append(item.identifier)
                        elif isinstance(item, symbol_table.ExpressionName):
                            if item.dot_separated_identifiers[-1] == self.field_name \
                                    and (
                                    (len(item.dot_separated_identifiers) == 2)
                                    or (len(item.dot_separated_identifiers) == 3 and item.dot_separated_identifiers[
                                0] == "this")
                            ) and (
                                    (item.dot_separated_identifiers[
                                         -2] in local_vars_of_superclass_type_or_others and len(
                                        item.dot_separated_identifiers) == 2)
                                    or item.dot_separated_identifiers[-2] in fields_of_superclass_type_or_others
                            ):
                                return False

        rewriter = symbol_table.Rewriter(program, self.filename_mapping)

        field = superclass.fields[self.field_name]
        if len(field.neighbor_names) == 0:
            rewriter.replace(field.get_tokens_info(), "")
            # Have to remove the modifiers too, because of the new grammar.
            for mod_ctx in field.modifiers_parser_contexts:
                rewriter.replace(symbol_table.TokensInfo(mod_ctx), "")
        else:
            i = field.index_in_variable_declarators
            var_ctxs = field.all_variable_declarator_contexts
            if i == 0:
                to_remove = symbol_table.TokensInfo(var_ctxs[i])
                to_remove.stop = symbol_table.TokensInfo(var_ctxs[i + 1]).start - 1  # Include the ',' after it
                rewriter.replace(to_remove, "")
            else:
                to_remove = symbol_table.TokensInfo(var_ctxs[i])
                to_remove.start = symbol_table.TokensInfo(var_ctxs[i - 1]).stop + 1  # Include the ',' before it
                rewriter.replace(to_remove, "")

        is_public = "public" in field.modifiers
        is_protected = "protected" in field.modifiers
        modifier = ("public " if is_public else ("protected " if is_protected else ""))
        for c in classes_to_add_to:
            c_body_start = symbol_table.TokensInfo(c.parser_context.classBody())
            c_body_start.stop = c_body_start.start  # Start and stop both point to the '{'
            rewriter.insert_after(c_body_start,
                                  (
                                          "\n    " + modifier + field.datatype + " "
                                          + self.field_name
                                          + ((" = " + field.initializer) if field.initializer is not None else "")
                                          + ";"
                                  )
                                  )

        rewriter.apply()
        return True


def main(project_dir, source_package, source_class, field_name, target_classes: list, *args, **kwargs):
    """


    """
    res = PushDownField(
        symbol_table.get_filenames_in_dir(project_dir),
        package_name=source_package,
        superclass_name=source_class,
        field_name=field_name,
        class_names=target_classes,
    ).do_refactor()
    if not res:
        logger.error("Cannot push-down field")
        return False
    return True


# Tests
def test():
    print("Testing pushdown_field...")
    filenames = [
        "../benchmark_projects/tests/pushdown_field/test1.java",
        "../benchmark_projects/tests/pushdown_field/test2.java",
        "../benchmark_projects/tests/pushdown_field/test3.java",
        "../benchmark_projects/tests/pushdown_field/test4.java",
        "../benchmark_projects/tests/pushdown_field/test5.java",
        "../benchmark_projects/tests/pushdown_field/test6.java",
        "../benchmark_projects/tests/pushdown_field/test7.java",
    ]
    PushDownField(filenames, "pushdown_field_test_vehicle", "Vehicle", "brand").do_refactor()

    if PushDownField(filenames[:2], "pushdown_field_test1", "A", "a").do_refactor():
        print("1, 2: Success!")
    else:
        print("1, 2: Cannot refactor.")

    for i in range(2, 7):
        if PushDownField(filenames[:2] + [filenames[i]], "pushdown_field_test1", "A", "a").do_refactor():
            print("1, 2, " + str(i + 1) + ": Success!")
        else:
            print("1, 2, " + str(i + 1) + ": Cannot refactor.")


if __name__ == "__main__":
    ant_dir = "D:/Dev/JavaSample"
    main(ant_dir,
         "your_package",
         "Unit",
         "fuel",
         ["Tank", ],
         )
