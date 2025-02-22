"""
The script implements automated refactoring to strategy design pattern

"""
__version__ = '1.4.2'
__author__ = 'Nader Mesbah, Morteza Zakeri'
__date__ = '20210108'

import argparse
from time import time

from antlr4 import *
from antlr4.TokenStreamRewriter import TokenStreamRewriter

from codart.gen.javaLabeled.JavaLexer import JavaLexer
from codart.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from codart.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class StrategyPatternRefactoringListener(JavaParserLabeledListener):
    """
    To implement the strategy pattern refactoring
    """

    def __init__(self, common_token_stream: CommonTokenStream = None, method_identifier: str = None):
        """
        :param common_token_stream:
        """
        self.i = 0
        self.enter_method = False
        self.token_stream = common_token_stream
        self.method_identifier = method_identifier
        self.class_identifier = ""
        self.currentClass = 1
        self.enter_class = False
        self.method_selected = False
        self.ifelse = False
        self.inputPara = False
        self.newClasses = ""
        self.interface = ""
        self.para = ""
        self.newPara = []
        self.oldPara = []
        self.typePara = []
        self.old_method_Declaration = ""
        self.new_method_Declaration = ""
        # Move all the tokens in the source code in a buffer, token_stream_rewriter.
        if common_token_stream is not None:
            self.token_stream_rewriter = TokenStreamRewriter(common_token_stream)
        else:
            raise TypeError('common_token_stream is None')

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.enter_class = True
        self.class_identifier = ctx.IDENTIFIER().getText()

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        grand_parent_ctx = ctx.parentCtx.parentCtx
        self.method_selected = False
        if ctx.IDENTIFIER().getText() == self.method_identifier:
            self.enter_method = True
            self.method_selected = True
            self.old_method_Declaration = self.token_stream_rewriter.getText("",
                                                                             grand_parent_ctx.modifier(
                                                                                 0).start.tokenIndex,
                                                                             ctx.formalParameters().stop.tokenIndex)
            self.old_method_Declaration = self.old_method_Declaration.replace(self.method_identifier, "doOperation")

    def enterStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        if self.method_selected:
            self.ifelse = True
            self.para = ctx.parExpression().expression().getText().split('==')
            # Define new concrete strategy as subclass of strategy
            new_sub_class = ("\nclass SubNewClass"
                             + str(self.currentClass)
                             + " implements MyStrategy{\n\t"
                             + "@Override\n\t" + self.old_method_Declaration
                             + "\n\t"
                             )
            body = self.token_stream_rewriter.getText("", ctx.statement(0).block().start.tokenIndex,
                                                      ctx.statement(0).block().stop.tokenIndex)

            # Make body for new subclass
            if body[0] != "{":
                body = "{" + body + "}"
            self.newClasses += new_sub_class + body + "\n}"
            self.currentClass += 1

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        if self.enter_method:
            if self.ifelse and self.inputPara:
                # Create new class(Create an interface of strategy class named MyStrategy)
                self.interface = "\ninterface MyStrategy {\n\t" + self.new_method_Declaration + ";\n}"
                self.newClasses = self.newClasses.replace(self.old_method_Declaration, self.new_method_Declaration)
                self.token_stream_rewriter.insertAfter(ctx.start.tokenIndex - 1,
                                                       text="\n" + self.interface + self.newClasses + "\n")
                self.enter_method = False
        self.enter_class = False

    def enterFormalParameter(self, ctx: JavaParserLabeled.FormalParameterContext):
        if self.method_selected:
            self.inputPara = True
            self.oldPara.append(ctx.typeType().getText() + " " + ctx.variableDeclaratorId().getText())
            self.typePara.append(ctx.typeType().getText())

    def exitMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        if self.method_selected:
            # Make new method declaration
            if self.ifelse and self.inputPara:
                self.newPara = []
                for item in self.oldPara:
                    if not item.endswith(str(self.para[0])):
                        self.newPara.append(item)
                self.newPara = ', '.join(self.newPara)
                LPRANindex = self.old_method_Declaration.index('(')
                self.new_method_Declaration = self.old_method_Declaration[:LPRANindex] + "(" + self.newPara + ")"
                new_name = self.old_method_Declaration.replace("doOperation", self.method_identifier + "Strategy")
                temp1 = ', '.join(self.oldPara)
                temp1 = "(" + temp1 + ")"
                temp2 = "(" + self.newPara + ")"
                new_name = new_name.replace(temp1, temp2)
                for item in self.typePara:
                    self.newPara = self.newPara.replace(item, "")
                # Modify original class
                newbody = (
                        " private MyStrategy strategy;\n"
                        + "\tpublic "
                        + self.class_identifier
                        + "(MyStrategy strategy){\n"
                        + "\t\tthis.strategy = strategy;\n"
                        + "\t}\n" + "\t" + new_name + "{\n"
                        + "\t\treturn strategy.doOperation("
                        + self.newPara + ");\n"
                        + "\t}"
                )

                self.token_stream_rewriter.replaceRange(
                    ctx.parentCtx.parentCtx.start.tokenIndex,
                    ctx.stop.tokenIndex,
                    newbody,
                )


def main(args):
    # Step 1: Load input source into stream
    begin_time = time()
    stream = FileStream(args.file, encoding='utf8', errors='ignore')
    # input_stream = StdinStream()
    print('Input stream:')
    print(stream)

    # Step 2: Create an instance of AssignmentStLexer
    lexer = JavaLexer(stream)
    # Step 3: Convert the input source into a list of tokens
    token_stream = CommonTokenStream(lexer)
    # Step 4: Create an instance of the AssignmentStParser
    parser = JavaParserLabeled(token_stream)
    parser.getTokenStream()
    # Step 5: Create parse tree
    parse_tree = parser.compilationUnit()
    # Step 6: Create an instance of the refactoringListener, and send as a parameter the list of tokens to the class
    my_listener = StrategyPatternRefactoringListener(common_token_stream=token_stream,
                                                     method_identifier='execute')
    #                                                     method_identifier='read')
    #                                                     method_identifier='write')

    walker = ParseTreeWalker()
    walker.walk(t=parse_tree, listener=my_listener)

    print('Compiler result:')
    print(my_listener.token_stream_rewriter.getDefaultText())

    with open('../../tests/strategy1/StrategyExample0.refactored.java', mode='w', newline='') as f:
        #    with open('StrategyExample1.refactored.java', mode='w', newline='') as f:
        #    with open('StrategyExample2.refactored.java', mode='w', newline='') as f:
        f.write(my_listener.token_stream_rewriter.getDefaultText())

    end_time = time()
    print("execute time : ", end_time - begin_time)


# Test driver
if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        '-n', '--file',
        help='Input source', default=r'StrategyExample0.java')
    #        help = 'Input source', default = r'StrategyExample1.java')
    #        help = 'Input source', default = r'StrategyExample2.java')
    args_ = argparser.parse_args()
    main(args_)
