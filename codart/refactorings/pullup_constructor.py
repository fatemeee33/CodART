"""
## Introduction

When subclasses grow and get developed separately, your code may have constructors that perform similar work.
Pull up constructor refactoring removes the repetitive method from subclasses and moves it to a superclass.


## Pre and post-conditions

### Pre-conditions:

1. The source package, class and constructor should exist.

2. The order of the params in the constructor should be equal in the child classes.

3. empty package name is addressable using "".


### Post Conditions:

No specific post-condition

"""

__version__ = '0.1.1'
__author__ = 'Morteza Zakeri'

import collections

# import logging

try:
    import understand as und
except ImportError as e:
    print(e)

from antlr4.TokenStreamRewriter import TokenStreamRewriter

from codart.gen.JavaParserLabeled import JavaParserLabeled
from codart.gen.JavaParserLabeledListener import JavaParserLabeledListener

from codart.symbol_table import parse_and_walk, Program

# Config logging
from codart.config import logger


# logging.basicConfig(filename='codart_result.log', level=logging.DEBUG)
# logger = logging.getLogger(os.path.basename(__file__))


class PullUpConstructorListener(JavaParserLabeledListener):
    """


    """

    def __init__(self, rewriter: TokenStreamRewriter, is_father: bool, class_name: str, has_father_con: bool,
                 common_sets: [], params: str):
        """


        """

        self.rewriter = rewriter
        self.is_father = is_father
        self.has_father_con = has_father_con
        self.class_name = class_name
        self.common_sets = common_sets
        self.params = params

        self.in_con = False
        self.delete = False

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        if self.is_father:
            code = ""
            for var in self.common_sets:
                code += f"this.{var} = {var};\n"
            if self.has_father_con:
                pass
            else:
                self.rewriter.insertBeforeToken(
                    token=ctx.stop,
                    text=f"public {self.class_name}({self.params})" + "{\n" + code + "}"
                )

    def enterConstructorDeclaration(self, ctx: JavaParserLabeled.ConstructorDeclarationContext):
        if not self.is_father:
            self.in_con = True

    def exitConstructorDeclaration(self, ctx: JavaParserLabeled.ConstructorDeclarationContext):
        is_valid = False
        for i in self.common_sets:
            if i in ctx.getText():
                is_valid = True
                break
        if self.is_father and self.has_father_con and is_valid:
            code = ""
            for var in self.common_sets:
                code += f"this.{var} = {var};\n"
            self.rewriter.insertBeforeToken(
                token=ctx.stop,
                text=code
            )
        self.in_con = False

    def enterExpression1(self, ctx: JavaParserLabeled.Expression1Context):
        if self.in_con:
            identifier = str(ctx.IDENTIFIER())
            if identifier in self.common_sets:
                self.delete = True

    def exitExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        if self.delete:
            self.rewriter.delete(
                program_name=self.rewriter.DEFAULT_PROGRAM_NAME,
                from_idx=ctx.start.tokenIndex,
                to_idx=ctx.stop.tokenIndex + 1
            )
        self.delete = False


def get_cons(program: Program, packagename: str, superclassname: str, class_name: str):
    """

    A function to complete the Pull-up constructor refactoring by finding all the classes with similar constructors.

    """
    extendedclass = []
    removemethods = {}
    removemethods1 = []
    removemethods3 = {}
    mets = program.packages[packagename].classes[class_name].methods
    met = []
    methodkey = ""
    for methodName, method in mets.items():
        if method.is_constructor:
            met = method
            methodkey = methodName
            break
    body_text_method = met.body_text
    parammethod = met.parameters

    for package_name in program.packages:
        package = program.packages[package_name]
        for class_ in package.classes:
            _class = package.classes[class_]

            if _class.superclass_name == superclassname:
                extendedclass.append(_class)

    i = 0
    for d in extendedclass:
        class_ = extendedclass[i]
        i = i + 1
        for mk in class_.methods:
            m_ = class_.methods[mk]
            m = mk[:mk.find('(')]
            if m_.body_text == body_text_method and m_.parameters == parammethod and m_.is_constructor:
                if class_.name not in removemethods:
                    removemethods[class_.name] = [methodkey]
                else:
                    removemethods[class_.name].append(methodkey)
            elif m_.is_constructor:
                listBody_text = body_text_method.replace("{", "").replace("}", "").split(";")
                listm_body = m_.body_text.replace("{", "").replace("}", "").split(";")
                s1 = set(listBody_text)
                s2 = set(listm_body)
                if s2.issubset(s1):
                    removemethods1.append(diff_lists(listBody_text, listm_body))
                    if class_.name not in removemethods:
                        removemethods[class_.name] = [mk]
                    else:
                        removemethods[class_.name].append(mk)
                elif s1.issubset(s2):
                    removemethods1.append(diff_lists(listm_body, listBody_text))
                    if class_.name not in removemethods:
                        removemethods[class_.name] = [mk]
                    else:
                        removemethods[class_.name].append(mk)
                else:
                    a = diff_lists(listBody_text, listm_body)
                    if class_.name not in removemethods3:
                        removemethods3[class_.name] = [a]
                    else:
                        removemethods3[class_.name].append(a)

                    if class_.name not in removemethods:
                        removemethods[class_.name] = [mk]
                    else:
                        removemethods[class_.name].append(mk)

    removemethods[class_name] = [methodkey]
    return removemethods, removemethods1


def diff_lists(li1, li2):
    return list(set(li1) - set(li2)) + list(set(li2) - set(li1))


def main(udb_path, source_package, target_class, class_names: list, *args, **kwargs):
    """

    """

    if len(class_names) < 2:
        logger.error("class_names is empty.")
        return False
    db = und.open(udb_path)
    parent_cons = []

    # Check children
    parent = db.lookup(f"{target_class}", "Public Class")
    if len(parent) != 1:
        logger.error("Count of target class is not 1.")
        db.close()
        return False
    parent = parent[0]
    parent_file = db.lookup(f"{target_class}.java", "File")[0].longname()

    for i in parent.ents("Define", "Constructor"):
        parent_cons.append(i.parameters())

    # Find constructor entities group by signature
    constructors = {}

    for child in class_names:
        cons = db.lookup(f"{child}.{child}", "Constructor")
        for con in cons:
            if con.parent() is not None:
                if source_package not in con.parent().longname():
                    logger.error("Source package does not match.")
                    db.close()
                    return False
            parameters = con.parameters()
            if parameters in constructors:
                constructors[parameters].append(con)
            else:
                constructors[parameters] = [con]

    # Find common statements
    for k in constructors:
        meta_data = {
            parent_file: {'is_father': True, 'has_father_con': k in parent_cons, 'class_name': parent.simplename()},
        }
        con = constructors[k][0]
        ents = []

        for ref in con.refs("Set"):
            data = {'is_father': False, 'has_father_con': k in parent_cons, 'class_name': con.parent().simplename()}
            if ref.file().longname() not in meta_data.keys():
                meta_data[ref.file().longname()] = data
            if target_class in ref.ent().longname():
                ents.append(ref.ent().simplename())

        for i in range(1, len(constructors[k])):
            con2 = constructors[k][i]
            for ref in con2.refs("Set"):
                data = {'is_father': False, 'has_father_con': k in parent_cons,
                        'class_name': con2.parent().simplename()
                        }
                if ref.file().longname() not in meta_data.keys():
                    meta_data[ref.file().longname()] = data
                if target_class in ref.ent().longname():
                    ents.append(ref.ent().simplename())

        ents = [item for item, count in collections.Counter(ents).items() if count > 1]
        if len(meta_data.keys()) > 1:
            for file_name in meta_data:
                data = meta_data[file_name]
                parse_and_walk(
                    file_name,
                    PullUpConstructorListener,
                    has_write=True,
                    is_father=data['is_father'],
                    has_father_con=data['has_father_con'],
                    common_sets=ents,
                    class_name=data['class_name'],
                    params=k
                )
    db.close()
    return True


# Tests
if __name__ == "__main__":
    main(
        "D:/Dev/JavaSample/JavaSample1.udb",
        "",
        "Employee",
        class_names=["Admin", "Manager", ]
    )
