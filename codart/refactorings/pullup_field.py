"""

## Introduction

When subclasses grow and get developed separately, identical (or nearly identical) fields and methods appear.
Pull up field refactoring removes the repetitive field from subclasses and moves it to a superclass.

## Pre- and Post-Conditions

### Pre Conditions:
1. There should exist a corresponding child and parent in the project.

2. The field that should be pulled up must be valid.

3. The duplicated field in children's classes and its class and package should be identified.

### Post Conditions:
1. The changed field's usages and callings will also change respectively.

2. There will be children and parents having their desired fields added or removed.

3. Check for multilevel inheritance.

"""

__version__ = '0.2.0'
__author__ = 'Morteza Zakeri'

# import shutil
import os
# from codart.utility.directory_utils import git_restore
from codart import symbol_table
from codart.config import logger, PROJECT_PATH
from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from antlr4.InputStream import InputStream
from codart.gen.JavaParserListener import JavaParserListener
from codart.gen.JavaParserVisitor import JavaParserVisitor
from codart.gen.JavaLexer import JavaLexer
from codart.gen.JavaParser import JavaParser


class PullUpFieldIdentification:
    """

        This  class identifies duplicated fields in children's class and
        provides information for calling pull up field refactoring to
        pull up duplicated fields to a common super class.

    """
    def __init__(self, directory_path):
        self.directory_path = directory_path
        self.package_map = {}
        self.field_signatures = {}

    class PackageExtractor(JavaParserListener):
        def __init__(self):
            self.package_name = None

        def enterPackageDeclaration(self, ctx):
            """
            Capture the package declaration from the parse tree.
            """
            self.package_name = ctx.qualifiedName().getText()

    def extract_packages(self):
        """
        Extract package declarations from all Java files in the directory.
        """
        for root, _, files in os.walk(self.directory_path):
            for file in files:
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    try:
                        input_stream = FileStream(file_path, encoding="utf-8")
                        lexer = JavaLexer(input_stream)
                        token_stream = CommonTokenStream(lexer)
                        parser = JavaParser(token_stream)
                        tree = parser.compilationUnit()

                        extractor = self.PackageExtractor()
                        walker = ParseTreeWalker()
                        walker.walk(extractor, tree)

                        self.package_map[file_path] = extractor.package_name or "default"
                    except Exception as e:
                        print(f"Error processing file {file_path}: {e}")

    class FieldVisitor(JavaParserVisitor):
        def __init__(self):
            self.fields = []  # List to store field details
            self.current_class = None  # Track the current class name

        def visitClassDeclaration(self, ctx):
            """
            Visit class declarations to track the current class.
            """
            self.current_class = ctx.IDENTIFIER().getText()  # Set the current class name
            self.visitChildren(ctx)  # Process fields in the class
            self.current_class = None  # Reset class name after leaving the class

        def visitFieldDeclaration(self, ctx):
            """
            Visit field declarations and extract field information.
            """
            field_type = ctx.typeType().getText()  # Get the field type
            variable_declarators = ctx.variableDeclarators().variableDeclarator()
            for declarator in variable_declarators:
                field_name = declarator.variableDeclaratorId().getText()  # Get the field name
                self.fields.append((field_type, field_name, self.current_class))
            return self.visitChildren(ctx)

    def extract_fields(self, file_path):
        """
        Parse a Java file to extract field declarations.
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        input_stream = InputStream(content)
        lexer = JavaLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = JavaParser(token_stream)

        tree = parser.compilationUnit()
        visitor = self.FieldVisitor()
        visitor.visit(tree)
        return visitor.fields

    def find_duplicate_fields(self):
        """
        Identify duplicate fields across classes in the directory.
        """
        duplicate_fields = []

        self.extract_packages()

        for root, _, files in os.walk(self.directory_path):
            for file_name in files:
                if file_name.endswith(".java"):
                    file_path = os.path.join(root, file_name)
                    fields = self.extract_fields(file_path)

                    for field_type, field_name, class_name in fields:
                        signature = f"{field_type} {field_name}"
                        package_name = self.package_map.get(file_path, "default")
                        if signature in self.field_signatures:
                            self.field_signatures[signature].append((class_name, package_name))
                        else:
                            self.field_signatures[signature] = [(class_name, package_name)]

        for signature, class_info in self.field_signatures.items():
            if len(class_info) > 1:
                field_name = signature.split(" ")[1]
                duplicate_fields.append((field_name, class_info))

        for field_name, class_info in duplicate_fields:
            print(f"'{field_name}' is duplicated in:")
            for class_name, package_name in class_info:
                print(f"Package: {package_name}, Class: {class_name}")

        return duplicate_fields


class PullUpFieldRefactoring:
    """

    The  class that does the process of pull up field refactoring.

    Removes the repetitive fields from the subclasses, creates the superclass,
    and moves the fields to the superclass.

    """

    def __init__(self, source_filenames: list,
                 package_name: str,
                 class_name: str,
                 field_name: str,
                 filename_mapping=lambda x: (x[:-5] if x.endswith(".java") else x) +
                 ".java", temp_dir="refactored_files"):
        """

        Args:

            source_filenames (list): A list of file names to be processed

            package_name (str): The name of the package in which the refactoring has to be done \
            (contains the classes/superclasses)

            class_name (str): Name of the class that the field is pulled up from

            field_name (str): Name of the field that has to be refactored

            filename_mapping (str): Mapping the file's name to the correct format so that it can be processed

        Returns:

            object (PullUpFieldRefactoring): An instance of PullUpFieldRefactoring class

        """
        self.source_filenames = source_filenames
        self.package_name = package_name
        self.class_name = class_name
        self.field_name = field_name
        self.filename_mapping = filename_mapping
        self.temp_dir = temp_dir

    # def copy_files(self):
    #     """Create a copy of original files in a temporary directory."""
    #     if not os.path.exists(self.temp_dir):
    #         os.makedirs(self.temp_dir)
    #
    #     for filename in self.source_filenames:
    #         # Copy each file to the temporary directory
    #         shutil.copy(filename, self.temp_dir)

    def do_refactor(self):
        # First, copy files
        # self.copy_files()
        program = symbol_table.get_program(self.source_filenames, print_status=False)
        # print(program.packages)

        if (
                self.package_name not in program.packages
                or self.class_name not in program.packages[self.package_name].classes
                or self.field_name not in program.packages[self.package_name].classes[self.class_name].fields
        ):
            logger.error("One or more inputs are not valid.")
            return False

        _class: symbol_table.Class = program.packages[self.package_name].classes[self.class_name]
        if _class.superclass_name is None:
            logger.error("Super class is none.")
            return False

        superclass_name = _class.superclass_name
        if not program.packages[self.package_name].classes.get(superclass_name):
            logger.error("Super class package is none!")
            return False

        superclass: symbol_table.Class = program.packages[self.package_name].classes[superclass_name]
        superclass_body_start = symbol_table.TokensInfo(superclass.parser_context.classBody())
        superclass_body_start.stop = superclass_body_start.start  # Start and stop both point to the '{'

        if self.field_name in superclass.fields:
            logger.error("Field is in superclass fields.")
            return False

        datatype = _class.fields[self.field_name].datatype

        fields_to_remove = []
        for pn in program.packages:
            p: symbol_table.Package = program.packages[pn]
            for cn in p.classes:
                c: symbol_table.Class = p.classes[cn]
                if (
                        (
                        (
                                c.superclass_name == superclass_name
                                and c.file_info.has_imported_class(self.package_name, superclass_name)
                        )
                        or (self.package_name is not None and c.superclass_name == superclass_name)
                        )
                        and
                        self.field_name in c.fields and c.fields[self.field_name].datatype == datatype
                ):
                    fields_to_remove.append(c.fields[self.field_name])

        if len(fields_to_remove) == 0:
            logger.error("No fields to remove.")
            return False

        is_public = False
        is_protected = True
        for field in fields_to_remove:
            field: symbol_table.Field = field
            is_public = is_public or "public" in field.modifiers
            is_protected = is_protected and ("protected" in field.modifiers or "private" in field.modifiers)

        rewriter = symbol_table.Rewriter(program, self.filename_mapping)

        rewriter.insert_after(superclass_body_start, "\n\t" + (
            "public " if is_public else (
                "protected " if is_protected else "")) + datatype + " " + self.field_name + ";")

        for field in fields_to_remove:
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
                    to_remove.stop = symbol_table.TokensInfo(
                        var_ctxs[i + 1]).start - 1  # Include the ',' after it
                    rewriter.replace(to_remove, "")
                else:
                    to_remove = symbol_table.TokensInfo(var_ctxs[i])
                    to_remove.start = symbol_table.TokensInfo(
                        var_ctxs[i - 1]).stop + 1  # Include the ',' before it
                    rewriter.replace(to_remove, "")

            # Add initializer to class constructor if initializer exists in field declaration
            if field.initializer is not None:
                _class: symbol_table.Class = program.packages[field.package_name].classes[field.class_name]
                initializer_statement = (field.name
                                         + " = "
                                         + ("new " + field.datatype + " " if field.initializer.startswith('{') else "")
                                         + field.initializer
                                         + ";")

                # Todo: Requires better handling
                if 'new' in initializer_statement and '()' in initializer_statement:
                    initializer_statement = initializer_statement.replace('new', 'new ')

                has_contructor = False
                for class_body_decl in _class.parser_context.classBody().getChildren():
                    if class_body_decl.getText() in ['{', '}']:
                        continue
                    member_decl = class_body_decl.memberDeclaration()
                    if member_decl is not None:
                        constructor = member_decl.constructorDeclaration()
                        if constructor is not None:
                            body = constructor.constructorBody  # Start token = '{'
                            body_start = symbol_table.TokensInfo(body)
                            body_start.stop = body_start.start  # Start and stop both point to the '{'
                            rewriter.insert_after(body_start, "\n\t" + initializer_statement)
                            has_contructor = True
                if not has_contructor:
                    body = _class.parser_context.classBody()
                    body_start = symbol_table.TokensInfo(body)
                    body_start.stop = body_start.start  # Start and stop both point to the '{'
                    rewriter.insert_after(body_start,
                                          "\n\t" + _class.modifiers[
                                              0] + " " + _class.name + "() { " + initializer_statement + " }"
                                          )

        rewriter.apply()

        # Todo: check for multilevel inheritance recursively.
        # if _class.superclass_name is not None:
        # PullUpFieldRefactoring(self.source_filenames, self.package_name, _class.superclass_name, "id").do_refactor()
        return True

    # def get_copied_filenames(self):
    #     """Returns the list of copied filenames."""
    #     return [os.path.join(self.temp_dir, f) for f in os.listdir(self.temp_dir) if f.endswith(".java")]


def main(project_dir: str, package_name: str, children_class: str, field_name: str):
    """


    """

    # print("Pull-up field")
    result = PullUpFieldRefactoring(
        symbol_table.get_filenames_in_dir(project_dir),
        package_name,
        children_class,
        field_name,
        temp_dir=project_dir + "/refactored"
        # lambda x: "tests/pullup_field_ant/" + x[len(ant_dir):]
    ).do_refactor()
    if result:
        print(f"Successfully pulled up field '{field_name}'.")
    else:
        print(f"Failed to pull up field '{field_name}'.")
    # print(f"Success pull-up field {field_name}" if result else f"Cannot  pull-up field {field_name}")
    return result


# Tests
def test1():
    print("Testing pullup_field...")
    filenames = [
        "D:/archive/uni/CD/project/CodART/tests/pullup_field/test5.java",
        "D:/archive/uni/CD/project/CodART/tests/pullup_field/test6.java",
        # "../benchmark_projects/tests/pullup_field/test1.java",
        # "../benchmark_projects/tests/pullup_field/test2.java",
        # "../benchmark_projects/tests/pullup_field/test3.java",
        # "../benchmark_projects/tests/pullup_field/test4.java"
    ]

    if PullUpFieldRefactoring(filenames, "pullup_field_test5", "C", "id").do_refactor():
        print("Success!")
    else:
        print("Cannot refactor.")


def test2():
    target_files = ["tests/apache-ant/main/org/apache/tools/ant/types/ArchiveFileSet.java",
                    "tests/apache-ant/main/org/apache/tools/ant/types/TarFileSet.java",
                    "tests/apache-ant/main/org/apache/tools/ant/types/ZipFileSet.java"
                    ]
    ant_dir = "/home/ali/Desktop/code/TestProject/"

    main(
        project_dir="/data/Dev/JavaSample/",
        package_name="your_package",
        children_class="Soldier",
        field_name="has_baby"
    )


def test3():
    main(
        project_dir=PROJECT_PATH,
        package_name="technology.tabula",
        children_class="Table",
        field_name="cells"
    )


def pull_up_field(path: str):
    identifier = PullUpFieldIdentification(directory_path=path)
    duplicate_fields = identifier.find_duplicate_fields()
    # git_restore(project_dir=path)
    for field_name, class_info in duplicate_fields:
        """
        Perform refactoring to pull up a duplicated field to a common superclass.
        """
        print(f"Refactoring field '{field_name}' from the following classes to a common superclass:")
        for class_name, package_name in class_info:
            print(f"Package: {package_name}, Class: {class_name}")
            main(project_dir=path, package_name=package_name, children_class=class_name, field_name=field_name)


if __name__ == "__main__":
    # test1()
    # test2()
    # test3()
    pull_up_field(path="C:/Users/98910/Desktop/test")
