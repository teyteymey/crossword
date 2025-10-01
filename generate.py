import sys

from crossword import *

from collections import deque, defaultdict


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()    # we start for all the words as options in a variable
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for variable in self.domains:
            self.domains[variable] = {
                word for word in self.domains[variable]
                if len(word) == variable.length
            }

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.

        From notes:
        Arc consistency is when all the values in a variable’s domain satisfy the variable’s binary constraints. 
        In other words, to make X arc-consistent with respect to Y, remove elements from X’s domain until every choice for X has a possible choice for Y.
        """
        # gives cell where they would cross if any
        overlaps = self.crossword.overlaps[x, y]

        # if they dont cross, return already
        if overlaps == None:
            return False

        remove_x_domain = []
        found_word_consistent = False
        # for each character in each word[overlaps[0]] of domain x, if we dont find another word in y[overlaps[1]] that equals, means that y
        # has no value that fits with x, so we remove it from x
        # 
        # ----- EXAMPLE -----
        # X: {'HELLO', 'AMAZE', 'TODAY', 'READY', 'FORGE'}; Y: {'ELM', 'ODE'}; OVERLAPS: (1, 2)
        # CHARS IN WORDS IN X IN POSITION 1 = [E, M, O, E, O].
        # CHARS IN WORDS IN Y IN POSITION 2 = [M, E].
        # So we have to remove words that dont overlap correctly, ones with O characted in the index 1 of the word (being 0 the first index). in this example TODAY and FORGE
        for word_x in self.domains[x]:
            for word_y in self.domains[y]:
                if word_x[overlaps[0]] ==  word_y[overlaps[1]]:
                    found_word_consistent = True
                    break
            if not found_word_consistent:
                remove_x_domain.append(word_x)
            # reset boolean for new iteration
            found_word_consistent = False

        if len(remove_x_domain) > 0:
            self.domains[x] = {
                word for word in self.domains[x]
                if word not in remove_x_domain
            }
            return True
        
        return False


    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        arcs_queue = deque()
        if arcs is None:
            
            # could have use overlaps.keys too i guess
            for variable in self.crossword.variables:
                for neighbor in self.crossword.neighbors(variable):
                    arcs_queue.append((variable, neighbor))
        else:
            for arc in arcs:
                arcs_queue.append(arc)

        
        while len(arcs_queue) > 0:
            arc = arcs_queue.popleft()
            # means theres been a change in x's domain and we should check further
            if self.revise(arc[0], arc[1]):
                # if no more possibilities for domain of x, no solution is possible
                if len(self.domains[arc[0]]) == 0:
                    return False
                # add all arcs to make sure is consistent except y cuz we just did it.
                for neighbor in self.crossword.neighbors(arc[0]):
                    if neighbor != arc[1]:
                        # the order is important to check neighbor against x. If adding (x, neighbor) we need to remove the check to work but im sure
                        # it does many more iterations
                        arcs_queue.append((neighbor, arc[0]))

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for variable in self.crossword.variables:
            if variable not in assignment:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # if repeated values
        if len(assignment.values()) != len(set(assignment.values())):
            return False
        
        for variable in assignment:
            # check that word assigned fits
            if variable.length != len(assignment[variable]):
                return False
            # check for each neighbor that the word assigned is consistent with the current word,
            # so that the character where they overlap is the same
            for neighbor in self.crossword.neighbors(variable):
                overlap_indexes = self.crossword.overlaps[variable, neighbor]
                # not supposed to check if the assignment is complete here, so its okay if neighbor is not assigned
                if neighbor in assignment and assignment[variable][overlap_indexes[0]] !=  assignment[neighbor][overlap_indexes[1]]:
                    return False
        
        return True


    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        dict_response = defaultdict(list)

        for word in self.domains[var]:
            count = 0
            for neighbor in self.crossword.neighbors(var):
                if neighbor not in assignment:
                    overlap_indexes = self.crossword.overlaps[var, neighbor]
                    for neighbord_word in self.domains[neighbor]:
                        # if characters dont match, it rules it out.
                        # do this for all the words in all the neighbors domains for each word in var
                        if word[overlap_indexes[0]] != neighbord_word[overlap_indexes[1]]:
                            count += 1
            dict_response[count].append(word)

        response = []
        # sorts them by asc key
        for item in sorted(dict_response.items()):
            for word in item[1]:
                response.append(word)

        return response

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        result = defaultdict(list)
        for variable in self.crossword.variables:
            if variable not in assignment:
                # adds the variable to the number of words in its domain
                result[len(self.domains[variable])].append(variable)
        
        # sort by count asc and variables that have that number of words in domain
        ordered_variables = sorted(result.items())
        #if the first element (so the one with the least words in its domain) has only one variable, return it.
        # else means that they have the same number of words and we need to untie them
        # item is a tuple of count and variables: (0, [var1, var2])
        variables_with_smaller_domain = ordered_variables[0][1]
        if ordered_variables and len(variables_with_smaller_domain) == 1:
            return variables_with_smaller_domain[0]
        else:
            max_neighbors = -1
            best_variable = None
            for variable in variables_with_smaller_domain:
                if len(self.crossword.neighbors(variable)) > max_neighbors:
                    max_neighbors = len(self.crossword.neighbors(variable))
                    best_variable = variable

            return best_variable
        

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        
        variable = self.select_unassigned_variable(assignment)
        for value in self.domains[variable]:
            assignment[variable] = value
            resulting_assignment = self.backtrack(assignment)
            if resulting_assignment is not None:
                return resulting_assignment
            assignment.pop(variable)

        return None

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
