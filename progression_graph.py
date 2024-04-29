import os
import pygame
from math import sqrt
from os.path import exists, splitext, basename
from pygame.locals import *

def syntax_error(y, expression):
    """Used to help handling file parsing errors"""
    raise SyntaxError('Could not parse save file at line %d: "%s"' %(y+1, expression))

class Palette:
    """Static class, used to store colors data"""
    text = (255, 255, 255)
    background = (40, 40, 43)
    neutral = (80, 80, 85)
    red = (255, 0, 0)

    # States base colors. Points and links colors are derived from them
    _states = ((255, 0, 0), (127, 127, 0), (0, 255, 0))

    link = [None]*3 # contains a nested list: [[todo normal, todo hovered, todo selected], [doing], [completed]]
    # same for box colors
    box_outer = [None]*3
    box_sep = [None]*3
    box_inner = [None]*3

    init = False # to make sure Palette is init

    @staticmethod
    def __init__():
        Palette.init = True

        for i, col in enumerate(Palette._states):
            # init link colors
            Palette.link[i] = (col, Palette.mult(col, 0.6, 127), Palette.mult(col, 0.3, 192))

            # init point colors
            Palette.box_outer[i] = (Palette.mult(col, 0.4, 50), Palette.mult(col, 0.4, 60), Palette.mult(col, 0.4, 80))
            Palette.box_sep[i] = (Palette.mult(col, 0.2, 0), Palette.mult(col, 0.2, 20), Palette.mult(col, 0.2, 40))
            Palette.box_inner[i] = (Palette.mult(col, 0.3, 100), Palette.mult(col, 0.3, 120), Palette.mult(col, 0.3, 150))

    @staticmethod
    def mult(col, x, add=0):
        """Changes the exposition of a color: x=1 does nothing, x=0 is black, and colors are clamped.
        You can also specify add, an offset applied to all the color's components.

        Warning: only supports RGB colors"""

        if x == 1 and not add: return col

        r, g, b = col[0]*x + add, col[1]*x + add, col[2]*x + add
        return (255 if r > 255 else r, 255 if g > 255 else g, 255 if b > 255 else b)
Palette.__init__()

def ask_input_box(message, cast, check=lambda s: len(s), max_width=400):
    """Input box, freezes other actions to ask for user value.
    Param cast: function used to check for input format
    Param check: lambda used to check if the entry value is valid"""

    # make a darkened background from the current screen state
    dark = pygame.Surface((Graph.W, Graph.H), SRCALPHA)
    dark.fill((0, 0, 0, 127))
    background = pygame.Surface((Graph.W, Graph.H))
    background.blit(screen, (0, 0))
    background.blit(dark, (0, 0))
    
    # make box for the UI
    pygame.draw.rect(background, Palette.background, Rect((Graph.W*0.2, Graph.H*0.2, Graph.W*0.6, Graph.H*0.6)))
    text = font.render(message, True, Palette.text)
    background.blit(text, (Graph.W/2 - text.get_width()/2, Graph.H*0.3))

    # init error text
    error_text = [font.render("Error: can't decode value", True, Palette.red),
                  font.render('  Error: text too long', True, Palette.red),
                  font.render('  Error: invalid value', True, Palette.red)]
    error_pos = (Graph.W/2 - error_text[0].get_width()/2, Graph.H*0.3 + 20)

    # loop until the user presses Enter
    string = ''
    run = True
    while run:
        enter = False # for when to try to get out of the loop
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.event.post(pygame.event.Event(QUIT))
                return
            elif event.type == KEYDOWN:
                if event.key == K_BACKSPACE: string = string[:-1]
                elif event.key == K_ESCAPE: return
                elif event.key == K_RETURN or event.key == K_KP_ENTER:
                    enter = True
                else:
                    string += event.unicode

        # add blinking cursor for displayed text
        blink = ticks()%1000 < 600
        text = font.render(string + ('_' if blink else ''), True, Palette.text)

        # handle incorrect value
        error = 0
        try: cast(string)
        except: error = 1
        if text.get_width() > max_width:
            error = 2
            # trim the displayed text
            temp = text
            text = pygame.Surface((max_width, 16), SRCALPHA)
            text.blit(temp, (0, 0))
        if not check(string): error = 3
        if enter and not error: run = False

        screen.blit(background, (0, 0))
        if error: screen.blit(error_text[error-1], error_pos)

        # draw actual textbox
        w = max(text.get_width() + (0 if blink else char_w), 200) # minimum input size
        x = Graph.W/2 - w/2
        y = Graph.H/2 - 8
        pygame.draw.rect(screen, Palette.neutral, Rect((x-4, y-4), (w+8, 24)))
        screen.blit(text, (x, y))

        pygame.display.flip()
        clock.tick(FPS)

    return cast(string)

def image_selector():
    """Graphical image selector, displays all loaded images into a grid for the user to select"""

    # get and resize all loaded images
    images = list(Manager.images.values())
    ids = list(Manager.images.keys())
    for i, image in enumerate(images):
        surf = image.surf
        w, h = surf.get_size()
        if w > h: w, h = 50, 50*h/w
        else: w, h = 50*w/h, 50
        images[i] = pygame.transform.scale(surf, (w, h))

    w = (Graph.W-50) // 90 # images in one row
    height = len(images)//w*90 + 50
    scroll = 0
    do_scroll = height > Graph.H

    run = True
    selection = None
    while run:
        for event in pygame.event.get():
            if event.type == QUIT:
                run = False
                selection = None
            elif event.type == MOUSEWHEEL and do_scroll:
                scroll = min(max(scroll - 20*event.y, 0), height-Graph.H)
            elif event.type == MOUSEBUTTONDOWN and selection is not None:
                run = False # clicked on an image

        screen.fill(Palette.background)

        # draw scrollbar if needed
        if do_scroll:
            y = scroll * Graph.H / (height-20)
            h = Graph.H*Graph.H/height - 20
            pygame.draw.rect(screen, Palette.text, Rect(Graph.W-15, 10+y, 5, h))

        # get mouse data and display images
        mx, my = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()[0]
        selection = None
        for i, image in enumerate(images):
            x, y = 50 + 90*(i%w), 50 + 90*(i//w) - scroll
            if -50 < y < Graph.H:
                if x-10 <= mx < x+60 and y-10 <= my < y+60:
                    # image hovered
                    pygame.draw.rect(screen, Palette.neutral, Rect(x-10, y-10, 70, 70))
                    if click:
                        selection = i # image clicked
                        run = False
                screen.blit(image, (x, y))

        pygame.display.flip()
        clock.tick(FPS)

    if selection is None: return
    return Manager.images[ids[selection]]

class Manager:
    """Manager for all objects. Should be used to create and remove new objects, as it manages the ID system."""

    # key: ID, value: object
    points = {}
    links = {}
    images = {}

    @staticmethod
    def new_obj(args, _class, _dict, id):
        """Adds a new object to the corresponding dictionary, assigns an ID if needed"""
        if id is None:
            id = 0 # get the first available ID, starting at 0
            while id in _dict: id += 1
        else: id = int(id)

        _dict[id] = _class(*args, id)
        return _dict[id]

    @staticmethod
    def new_point(x, y, rank, state, id=None):
        result = Manager.new_obj((float(x), float(y), int(rank), int(state)), Point, Manager.points, id)

        # sort points to display the more important ones on top
        keys = sorted(Manager.points.keys(), key=lambda key: Manager.points[key].rank)
        copy = dict(Manager.points)
        Manager.points = {}
        for key in keys:
            Manager.points[key] = copy[key]

        return result

    @staticmethod
    def new_link(p1, p2, id=None):
        p1 = Manager.points[int(p1)]
        p2 = None if p2 is None else Manager.points[int(p2)]
        return Manager.new_obj((p1, p2), Link, Manager.links, id)

    @staticmethod
    def new_image(name, id=None):
        return Manager.new_obj((name,), Image, Manager.images, id)

    @staticmethod
    def attach_image(point_id, image_id):
        """Sets the image reference of a point"""
        Manager.points[int(point_id)].set_image(Manager.images[int(image_id)])

    @staticmethod
    def attach_text(point_id, text):
        """Sets the text of a point"""
        Manager.points[int(point_id)].set_text(None if text == '' else text)

    @staticmethod
    def reset():
        Manager.points = {}
        Manager.links = {}
        Manager.images = {}

class GraphObject:
    def update(self, events):
        raise NotImplementedError

    def collide(self, pos):
        raise NotImplementedError

class Point(GraphObject):
    """Point in the graph, can be attached to various links and have text and an image"""
    N_RANKS = 5
    rank_sizes = [40, 50, 60, 80, 100]
    assert len(rank_sizes) == N_RANKS

    def __init__(self, x, y, rank, state, id):
        self.x = x
        self.y = y
        self.state = state
        self.id = id

        self.text = None # text, None for no text
        self.image = None # image, None for no image

        self._surf = None # should always contain the surface with the right size
        # rendered pygame fonts, None for no text
        # if text, will contain [shortened text, full text (on hover/selection)]
        self._text_surfs = None
        self._size = None # should contain the size according to self.rank

        self.set_rank(rank) # init self.rank, self.size and self.surfs

    @staticmethod
    def get_rank_size(rank):
        """Returns the size from a particular point rank, handles incorrect values"""
        rank = min(max(rank, 0), Point.N_RANKS-1)
        return Point.rank_sizes[rank]

    def set_rank(self, rank):
        self.rank = rank
        self._size = Point.get_rank_size(rank)
        self.set_image(self.image)

        # update attached links
        for link in Manager.links.values():
            if self == link.p1 or self == link.p2:
                link.refresh()

    def cycle_rank(self):
        self.set_rank((self.rank+1) % Point.N_RANKS)

    def cycle_state(self):
        # order: todo, completed, doing
        self.state = (self.state-1) % 3
        self.set_image(self.image) # update self._surf

        for link in Manager.links.values():
            if self == link.p1 or self == link.p2:
                link.refresh()

    @staticmethod
    def black_back(surf):
        """Adds a semi-transparent Palette.background background to a surface"""
        new = pygame.Surface(surf.get_size(), SRCALPHA)

        black = pygame.Surface(surf.get_size(), SRCALPHA)
        black.fill(Palette.background)
        black.set_alpha(127)
        new.blit(black, (0, 0))
        new.blit(surf, (0, 0))

        return new

    def set_text(self, text):
        """Sets the point's text and updates its text Surface"""
        self.text = text
        if text is None:
            self._text_surfs = None
        else:
            max_width = 100
            if len(text)*char_w2 > max_width:
                # make unselected surface: cut text
                surf = font2.render(text[:int(max_width/char_w2)-3]+'...', True, Palette.text)
                self._text_surfs = [Point.black_back(surf), None]

                # make selected surface: word wrap if necessary
                # get words and split them if bigger than max_width
                words = []
                for word in text.split(' '):
                    while len(word)*char_w2 > max_width:
                        i = int(max_width/char_w2)-1
                        add, word = word[:i]+'-', word[i:]
                        words.append(add)
                    words.append(word)

                lines = ['']
                i = 0
                for word in words:
                    space = ' ' if lines[i] else ''
                    if len(lines[i]+space+word) * char_w2 > max_width:
                        if lines[i] == '':
                            lines[i] += word
                            lines.append('')
                        else: lines.append(word)
                        i += 1
                    else:
                        lines[i] += space+word

                # assemble lines into one surface
                width = len(max(lines, key=lambda l: len(l)))*char_w2
                surf = pygame.Surface((width, 12*len(lines)), SRCALPHA)
                for y, line in enumerate(lines):
                    line = font2.render(line, True, Palette.text)
                    surf.blit(line, (width/2 - line.get_width()/2, y*12))

                self._text_surfs[1] = Point.black_back(surf)
            else:
                # same text for both unselected and selected
                surf = Point.black_back(font2.render(text, True, Palette.text))
                self._text_surfs = [surf, surf]

    def set_image(self, image):
        """Sets and resizes self.surfs depending on self.size"""
        s = self._size
        self.image = image
        self._surfs = [None]*3

        # draw empty box
        m = int(self._size/10) # outline margin
        if m > 5: m = 5

        for i in range(3): # set normal, hovered, and selected surfaces
            self._surfs[i] = pygame.Surface((s, s))
            self._surfs[i].fill(Palette.box_outer[self.state][i])
            pygame.draw.rect(self._surfs[i], Palette.box_sep[self.state][i], Rect(m-1, m-1, s - m*2 + 2, s - m*2 + 2))
            pygame.draw.rect(self._surfs[i], Palette.box_inner[self.state][i], Rect(m, m, s - m*2, s - m*2))

        # if image, resize it and add it to the surface
        if image is not None:
            w, h = image.surf.get_size()
            s -= m*2 + 2
            if w > h: w, h = s, s*h/w
            else: w, h = s*w/h, s

            image = pygame.transform.scale(image.surf, (w, h))
            for i in range(3):
                self._surfs[i].blit(image, (m+1, m+1))

    def collide(self, pos):
        """Checks if the given position in screen coordinates intersects with the point"""
        x, y = graph.get_pos(self.x, self.y)
        s = self._size/2
        return x-s < pos[0] < x+s and y-s < pos[1] < y+s

    def visible(self):
        """Returns True if visible, taking scroll and zoom into account, otherwise returns False"""
        x, y = graph.get_pos(self.x, self.y)
        s = self._size/2
        return -s <= x < Graph.W+s and -s <= y < Graph.H+s

    def update(self, events):
        """Called by grah update() each frame"""
        x, y = graph.get_pos(self.x, self.y)

        # use a different texture when hovered
        i = 2 if self == graph.selection else 1 if self == graph.hovered else 0
        screen.blit(self._surfs[i], (x - self._size/2, y - self._size/2))

        # draw text
        if self._text_surfs is not None:
            t = self._text_surfs[bool(i)]
            screen.blit(t, (x - t.get_width()/2, y + self._size/2 + 5))

class Link(GraphObject):
    """Link between two points in the graph"""

    rank_sizes = [2, 3, 5, 8, 15]
    assert len(rank_sizes) == Point.N_RANKS

    def __init__(self, p1, p2, id):
        self.id = id

        # linked points
        self.p1 = p1
        self.p2 = p2 # can be None if just created

        self.refresh() # set self.rank, self.size and self._state

    @staticmethod
    def get_rank_size(rank):
        """Returns the size from a particular link rank, handles incorrect values"""
        rank = min(max(rank, 0), Point.N_RANKS-1)
        return Link.rank_sizes[rank]

    def refresh(self):
        """Triggered for all links when a point changes rank or state, to update the link's properties"""
        if self.p2 is None: self.rank = self.p1.rank
        else: self.rank = max(self.p1.rank, self.p2.rank)

        self._size = Link.get_rank_size(self.rank)

        if self.p2 is None: self._state = self.p1.state
        else: self._state = max(self.p1.state, self.p2.state)

    def collide(self, mpos):
        """Checks if the link collides with the mouse, with self._size tolerance.
        How it works:
        Let p1 and p2 be the two link ends once projected into screen space, and M the mouse pos.
        Let (D) be the line between p1 and p2, and M' the approximation of M projected onto (D).
        M' is hence the point in (D) that is at the same distance from p1 as M.

        The goal of this method is to compute the distance (squared) between M' and M,
        and compare it to self._size (squared). If the former is smaller, a collision is registered.

        During the calculation, we compute t, directional vector of (D). If t is not in [0, 1],
        the projected point is outside the segment of (D) that sits between p1 and p2,
        hence there is no collision in this case.

        In case p1 == p2, the line formed by the link is treated as a circle of radius self._size
        for collision checks. This shouldn't usually matter as the ends of the links are points
        and their collision detection runs first in Graph.update.
        """
        x1, y1 = graph.get_pos(self.p1.x, self.p1.y)
        x2, y2 = graph.get_pos(self.p2.x, self.p2.y)
        xm, ym = mpos
        s2 = self._size*self._size
        if x1 == x2 and y1 == y2:
            dx, dy = xm-x1, ym-y1
            return dx*dx + dy*dy <= s2

        # calculate t
        dx, dy = xm-x1, ym-y1
        p1_m = dx*dx + dy*dy
        dx, dy = x2-x1, y2-y1
        p1_p2 = dx*dx + dy*dy
        t = sqrt(p1_m/p1_p2)
        if t < 0 or t > 1: return False

        # calculate M' position
        xm2, ym2 = x1 + dx*t, y1 + dy*t

        dx, dy = xm-xm2, ym-ym2
        return dx*dx + dy*dy <= s2

    def update(self, events):
        """Called by grah update() each frame"""

        # get end points screen coordinates
        pos1 = graph.get_pos(self.p1.x, self.p1.y)
        if self.p2 is None:
            # the link is currently being drawn
            pos2 = pygame.mouse.get_pos()
        else: pos2 = graph.get_pos(self.p2.x, self.p2.y)

        # get color depending on if the link is hovered/selected
        i = 2 if self == graph.selection else 1 if self == graph.hovered else 0
        col = Palette.link[self._state][i]
        pygame.draw.line(screen, col, pos1, pos2, self._size)

class Image:
    """Pygame surface loaded from image file"""
    def __init__(self, path, id):
        self.name = splitext(basename(path))[0]
        self.path = path
        self.surf = pygame.image.load(path)
        self.id = id

class UI:
    """UI elements on top of the screen: help, info about selection"""
    def __init__(self):
        self.surf = pygame.Surface((Graph.W, 40), SRCALPHA) # blitted, cached surface
        self.text = ['P: new point, S: save file, O: open file, I: load image, Z: reset zoom',
                     'Del: delete link']
        # edit texts to discriminate between deleting a point, its image or its text
        text = 'L: start link, I: add image, T: add text, Del: delete %s, R: cycle rank, C: cycle state'
        self.text.append(text %'point')
        self.text.append(text %"text")
        self.text.append(text %"image")

        # transform the texts into text surfaces
        self.text = [font.render(text, True, Palette.text) for text in self.text]

    def update_surf(self):
        """Updates cached Surface: redraws background, adds elements depending on selection"""
        pygame.draw.rect(self.surf, Palette.neutral, Rect((0, 0), (Graph.W, 40)))

        if graph.selection is None:
            self.surf.blit(self.text[0], (12, 12))
        elif type(graph.selection) == Link:
            self.surf.blit(self.text[1], (12, 12))
        elif type(graph.selection) == Point:
            i = 4 if graph.selection.image is not None else 3 if graph.selection.text is not None else 2
            self.surf.blit(self.text[i], (12, 12))

    def update(self):
        self.surf.set_alpha(100 if pygame.mouse.get_pos()[1] < 40 else 255)
        screen.blit(self.surf, (0, 0))

class Graph:
    """Graph manager, for displaying the graph, handling scroll, and updating elements"""
    W = 900
    H = 500

    def __init__(self):
        assert Palette.init

        self.scroll_x = 0
        self.scroll_y = 0
        self.zoom = 1
        self.unit_size = 100 # graph unit to pixel ratio

        self.save_file = None

        # movement utilities
        self.drag_start = None # moved/scroll element pos when drag started
        self.drag_mouse_start = None # mouse pos when drag started

        self.selection = None # selected GraphPoint, or None if no selection
        self.hovered = None # hovered Graphpoint
        self.hovered = None # hovered Link (separate them to avoid issues when drawing a link)
        self.link = None # if link in construction, store it here, else None

        self.ui = UI()

        # debug information
        self._debug_surf = None

    def debug(self, *args):
        """Adds debug information to be displayed in self.update, deprecated unless in development.
        *args: many arguments that will be added to the debug string with space separators.
        There should not be newlines in there, artifacts can appear."""
        text = ' '.join(str(a) for a in args)
        width = len(text)*char_w

        if self._debug_surf is None:
            # create new Surface
            self._debug_surf = pygame.Surface((width, 16))
            y = 0
        else:
            # append text in a new line
            w, h = self._debug_surf.get_size()
            width = w if w > width else width
            surf = pygame.Surface((width, h+16))
            surf.blit(self._debug_surf, (0, 0))
            self._debug_surf = surf
            y = h

        self._debug_surf.blit(font.render(text, True, Palette.text), (0, y))

    def open(self, save_file):
        """Sets self.save_file and loads save file"""
        self.save_file = save_file
        
        # reset variables
        self.drag_start = None
        self.drag_mouse_start = None
        self.selection = None
        self.hovered = None
        self.hovered_l = None
        self.link = None
        self.ui.update_surf()

        Manager.reset()

        # TODO: handle deletion of old objects

        with open(save_file) as f: lines = f.read().split('\n')
        for y, raw in enumerate(lines):
            # format line: remove leading and trailing spaces, double spaces, comments
            line = ''
            prev = ' '
            for c in raw:
                if c == prev == ' ': continue
                if c == '#': break
                line += c
                prev = c
            line = line.rstrip()
            if not line: continue

            # get command from line
            line = line.split(' ')
            cmd = line[0]
            args = line[1:]

            # execute action depending on command
            match cmd:
                case 'P': # add new point
                    if len(args) != 5: syntax_error(y, raw)
                    Manager.new_point(*args)
                case 'L': # add new link
                    if len(args) != 3: syntax_error(y, raw)
                    Manager.new_link(*args)
                case 'I': # add new image
                    if len(args) != 2: syntax_error(y, raw)
                    Manager.new_image(*args)
                case 'Ai': # attach an image to a point
                    if len(args) != 2: syntax_error(y, raw)
                    Manager.attach_image(*args)
                case 'At': # attach text to a point
                    if len(args) != 2: syntax_error(y, raw)
                    Manager.attach_text(*args)
                case _: syntax_error(y, raw)

    def save(self):
        """Saves graph contents into self.save_file"""
        content = []

        if self.save_file is None: raise ValueError('No save loaded')

        # points
        content.append('# POINTS')
        for id, point in Manager.points.items():
            content.append('P %f %f %d %d %d' %(point.x, point.y, point.rank, point.state, id))

        # links
        content += ('', '# LINKS')
        for id, link in Manager.links.items():
            content.append('L %d %d %d' %(link.p1.id, link.p2.id, id))

        # images
        content += ('', '# IMAGES')
        for id, image in Manager.images.items():
            # check if this image is used in the graph, otherwise don't save it
            used = False
            for point in Manager.points.values():
                if point.image == image:
                    used = True
                    break
            
            if used:
                content.append('I %s %d' %(image.path, image.id))

        # images attached to points
        content += ('', '# LINK IMAGES')
        for id, point in Manager.points.items():
            if point.image is not None:
                content.append('Ai %d %d' %(id, point.image.id))

        # text attached to points
        content += ('', '# TEXT')
        for id, point in Manager.points.items():
            if point.text is not None:
                content.append('At %d %s' %(id, point.text))

        # save into file
        with open(self.save_file, 'w') as f: f.write('\n'.join(content)+'\n')

    def get_pos(self, x, y):
        """Returns the position, in screen coordinates, corresponding to a position in graph coordinates"""
        z = self.zoom * self.unit_size
        return (x - self.scroll_x) * z + self.W/2, (y - self.scroll_y) * z + self.H/2

    def from_pos(self, x, y):
        """Returns the position, in graph coordinates, corresponding to a position in screen coordinates"""
        z = self.zoom * self.unit_size
        return (x - self.W/2) / z + self.scroll_x, (y - self.H/2) / z + self.scroll_y

    def select(self, obj):
        """Sets self.selection to obj and updates self.ui"""
        self.selection = obj
        self.ui.update_surf()

    def update(self, events):
        """Updates objects and menu, displays the graph"""
        # move and zoom
        pressed = pygame.mouse.get_pressed()[0]
        mpos = pygame.mouse.get_pos()

        # get visible graph objects now, useful for collision checks
        visible_p = [] # points objects that are visible
        for point in Manager.points.values():
            if point.visible():
                visible_p.append(point)
        visible_l = [] # same for links
        for link in Manager.links.values():
            if link.p1 in visible_p or link.p2 in visible_p or link.p2 is None or True:
                visible_l.append(link)
 
        self.hovered = None
        for point in visible_p:
            if point.collide(mpos):
                self.hovered = point
                break
        for link in visible_l:
            # don't select a link if something else has been selected,
            # or if currently creating a link
            if self.hovered is not None or self.link is not None: break
            if link.collide(mpos): self.hovered = link

        # events check
        for event in events:
            # start dragging
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                self.select(self.hovered)

                if self.selection is None:
                    self.drag_start = (self.scroll_x, self.scroll_y)
                elif type(self.selection) == Point:
                    self.drag_start = (self.selection.x, self.selection.y)
                if type(self.selection) != Link:
                    self.drag_mouse_start = event.pos

                # finish adding a link
                if type(self.selection) == Point and self.link is not None and self.link.p1 != self.selection:
                    # check if no link exists between these two points
                    ok = True
                    for link in Manager.links.values():
                        if (link.p1 == self.link.p1 and link.p2 == self.selection) or \
                            (link.p2 == self.link.p1 and link.p1 == self.selection):
                            ok = False
                            break

                    if ok:
                        self.link.p2 = self.selection
                        self.link.refresh()
                        self.link = None
                        self.select(None)
                        self.drag_start = None # prevent unwanted drag

            # stop dragging
            elif event.type == MOUSEBUTTONUP and event.button == 1:
                self.drag_start = None
                self.drag_mouse_start = None

            # zoom
            elif event.type == MOUSEWHEEL and not pressed:
                if event.y > 0: self.zoom *= 1.2 # zoom in
                elif self.zoom > 0.01: self.zoom /= 1.2 # zoom out
                else: self.zoom = 0.01 # min zoom

            # keys
            elif event.type == KEYDOWN:
                if event.key == K_z: self.zoom = 1
                elif event.key == K_ESCAPE:
                    if self.link is None:
                        # unselect by hitting Escape
                        self.select(None)
                    else:
                        # or undo the creation of a new link
                        del Manager.links[self.link.id]
                        self.link = None
                elif event.key == K_RETURN and self.link is None:
                    self.select(None)
                elif self.selection is None:
                    if event.key == K_p:
                        Manager.new_point(*self.from_pos(*mpos), 0)
                    elif event.key == K_s:
                        self.save()
                    elif event.key == K_o:
                        path = ask_input_box('Enter save file', str, lambda s: exists(s))
                        if path is not None: self.open(path)
                    elif event.key == K_i:
                        path = ask_input_box('Enter valid image path:', str, check=lambda s: exists(s))
                        if path is not None: Manager.new_image(path)
                elif type(self.selection) == Point:
                    if event.key == K_l and self.link is None:
                        self.link = Manager.new_link(self.selection.id, None)
                    elif event.key == K_i:
                        image = image_selector()
                        if image is not None: self.selection.set_image(image)
                    elif event.key == K_t:
                        check = lambda s: len(s) and '\n' not in s and '\r' not in s and '\t' not in s
                        text = ask_input_box('Enter point text:', str, check, self.W-20)
                        if text is not None:
                            self.selection.set_text(text)
                    elif event.key == K_r:
                        self.selection.cycle_rank()
                    elif event.key == K_c:
                        self.selection.cycle_state()
                    elif event.key == K_DELETE:
                        if self.selection.image is not None:
                            self.selection.set_image(None)
                        elif self.selection.text is not None:
                            self.selection.set_text(None)
                        else:
                            to_delete = [] # links that connect to the deleted point
                            for id, link in Manager.links.items():
                                if link.p1 == self.selection or link.p2 == self.selection:
                                    to_delete.append(id)
                            del Manager.points[self.selection.id]
                            for link in to_delete:
                                del Manager.links[link]
                            self.selection = None
                        self.select(self.selection) # update self.ui
                elif type(self.selection) == Link:
                    if event.key == K_DELETE:
                        del Manager.links[self.selection.id]
                        self.select(None)

        if self.drag_start is not None:
            x, y = self.drag_start
            x0, y0 = self.drag_mouse_start
            x1, y1 = pygame.mouse.get_pos()
            m = 1/self.zoom/self.unit_size
            dx = (x0-x1) * m
            dy = (y0-y1) * m
            if type(self.selection) == Point:
                self.selection.x = x - dx
                self.selection.y = y - dy
            else:
                self.scroll_x = x + dx
                self.scroll_y = y + dy

        screen.fill(Palette.background)

        # update and render graph objects
        for link in visible_l: link.update(events)
        for point in visible_p: point.update(events)

        # update and render menu and UI
        self.ui.update()

        # display debug screen if needed
        if self._debug_surf is not None:
            screen.blit(self._debug_surf, (0, 0))
            self._debug_surf = None

FPS = 60
pygame.init()

screen = pygame.display.set_mode((Graph.W, Graph.H))
pygame.display.set_caption('Progression graph')
font = pygame.font.SysFont('consolas', 16)
font2 = pygame.font.SysFont('consolas', 12)
clock = pygame.time.Clock()
ticks = pygame.time.get_ticks

# get the characters length (fonts should be monospace)
char_w = font.render('_', True, Palette.text).get_width()
char_w2 = font2.render('_', True, Palette.text).get_width()

graph = Graph()
graph.open('test_save.txt')

dt = 0 # time passed in last frame, in seconds
run = True
while run:
    # handle pygame event loop
    events = pygame.event.get()
    for event in events:
        if event.type == QUIT: run = False

    graph.update(events)
    pygame.display.flip()
    dt = clock.tick(FPS)/1000

pygame.quit()
