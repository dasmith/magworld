#
# Blind, two-dimensional, rotationless agent simulation
#
# You are the red square.
#
# Instructions
#
#    i, j, k, l  =  move
#    m           =  toggle magnetism on/off (so we can pull, not just push)
#    b           =  toggle blind mode
#    q           =  quit
#
# When you collide with an object, you will be stopped.  But you can
# push on the object by simply pressing the motion key again.


import pygame
from pygame.time import Clock
import sys
from math import sqrt, pi, sin, cos, atan2

### Globals -------------------------------------------------------

# size of the world, in cells
M = N = 200

# how many pixels to use for each cell
cellsize = 5

############################################################
### useful constants

# center of window
cx, cy = M/2,N/2

red = (255,0,0)
magenta = (255,0,255)
green = (0,255,0)
orange = (255,128,0)
yellow = (255,255,0)
blue = (0,0,255)
darkBlue = (0,0,128)
white = (255,255,255)
black = (0,0,0)
pink = (255,200,200)
gray = (220, 220, 220)

cardinal_directions = ((-1,0),
                       (1,0),
                       (0,-1),
                       (0,1))

############################################################
# This class represents an object in the world.
class Body:
    def __init__(self, points, x, y, color=black, name="?", fixed=False):
        self.x = x
        self.y = y
        self.points = set(points) # each point is an (x,y) offset
        self.color = color
        self.name = name
        self.fixed = fixed

    # if i go from this body in the direction (dx,dy), do I touch body?
    def contacts(self, dx, dy, body):
        if body == self: return False

        # offset
        ox = self.x + dx - body.x
        oy = self.y + dy - body.y
        
        for x, y in self.points:
            if (x+ox, y+oy) in body.points:
                return True
        return False

    def neighbors(self, dx, dy):
        return [body for body in bodies if self.contacts(dx, dy, body)]

    def self_and_all_pickable_neighbors(self):
        ret = set([self])
        for dx, dy in cardinal_directions:
            for n in self.neighbors(dx,dy):
                if not n == arena:
                    ret.add(n)
        return ret

    def build_contact_subtree(self, dx, dy, accum):
        if not self in accum:
            accum.add(self)
            for neighbor in self.neighbors(dx, dy):
                neighbor.build_contact_subtree(dx, dy, accum)
        
    def contact_subtree(self, dx, dy):
        ret = set()
        self.build_contact_subtree(dx, dy, ret)
        return ret

    def __repr__(self):
        return self.name

### Helper code for building bodies

def hline(x, y, w):
    return [(i,y) for i in xrange(x,x+w)]

def vline(x, y, h):
    return [(x,j) for j in xrange(y,y+h)]

def rect(w,h):
    return [(i,0) for i in xrange(w)] \
        + [(i,h-1) for i in xrange(w)] \
        + [(0,j) for j in xrange(1,h-1)] \
        + [(w-1,j) for j in xrange(1,h-1)]


class Rect(Body):
    def __init__(self, w, h, x, y, **kwargs):
        points = rect(w,h)
        Body.__init__(self, points, x, y, **kwargs)



##########################################################
### Actually build a few bodies

agentbody = Rect(13, 13, 30, 50, color=red, name='agent')
arena = Body(rect(190,190)+
             hline(12, 110, 170)+
             vline(100,5,20)+
             vline(100,50,130)+
             vline(102,5,20)+
             vline(102,50,130)
             ,
             4, 4,
             color=gray, name='arena', fixed=True)
bodies = [agentbody, arena,
          Rect(10, 10, 30, 30, color=blue, name='blue'),
          Rect(1, 50, 105, 20, color=blue, name='door'),
          Rect(10, 10, 60, 30, color=green, name='green'),
          Rect(5, 10, 60, 20, color=orange, name='orange'),
          Rect(2, 2, 13, 125, color=orange, name='reward'),
          Body(hline(0,0,4)+
               vline(4,0,15)+
               hline(4,15,3)+
               vline(7,15,4)+
               hline(0,19,8)+
               vline(0,0,19),
               70,20,
               name='L')
          ]
               
##################################################################
# drawing code            

# world to pixel
def wtop(world):
    wx, wy = world
    return (wx * cellsize, wy * cellsize)


def draw():

    # hide objects, show sensor values
    if blind_mode:

        for dx, dy in agentbody.points:
            pygame.draw.rect(screen, agentbody.color,
                             wtop((cx + dx,
                                   cy + dy))
                             + (cellsize, cellsize))

        offsets = ((-1,6),
                   (13,6),
                   (6,-1),
                   (6,13),
                   )
        for (dx, dy), (ox, oy) in zip(cardinal_directions, offsets):
            if agentbody.neighbors(dx, dy):
                pygame.draw.rect(screen, blue,
                                 wtop((ox + cx, oy + cy))
                                 + (cellsize, cellsize))

        motion_indicators = {(1,0): (10,6),
                             (-1,0): (2,6),
                             (0,1): (6,10),
                             (0,-1): (6,2)}

        if adx or ady:
            ix, iy = motion_indicators[adx,ady]
            pygame.draw.rect(screen, green,
                             wtop((cx + ix, cy + iy))
                             + (cellsize, cellsize))
            
            
        if magnetism:
            pygame.draw.rect(screen, magenta,
                             wtop((cx+6, cy+6))
                             + (cellsize, cellsize))
            
            
            
    
    else:
        for body in bodies:
            for dx,dy in body.points:
                pygame.draw.rect(screen, body.color,
                                 wtop((body.x + dx,
                                       body.y + dy))
                                 + (cellsize, cellsize))

            





##################################################################
# pygame setup


pygame.init()
screen = pygame.display.set_mode((M*cellsize,N*cellsize))
screen.fill(white)
clock = Clock()


blind_mode = False

               
##################################################################
# the actual simulation code

t = 0

# The following diagram shows the dynamics of the system.
#
# world_state[0], effectors[0]
#           |      |    
#        evolve_world()
#           |      |
#           |    sensors[1]
#           |        |
#           |      behave()
#           |        |
# world_state[1], effectors[1]
#           |      |    
#        evolve_world()
#           |      |
# etc.

# World state consists of the following variables:

temp_stop = False   # whether the agent has been stopped due to a
                    # collision

contacts = None     # bodies currently moving with the agent, or None
                    # if the agent isn't moving

holding = set()
# Effectors consist of

mdx = mdy = 0       # motion we're trying to make
magnetism = False   # whether or not magnetism is on

# Sensors consist of

adx = ady = 0       # motion just made

pickup = 0
drop = 0
# Given the current world state and effectors, compute new world state
# and sensor values
def evolve_world():
    global adx, ady, mdx, mdy, pickup, drop, contacts, temp_stop, holding

    # is agent trying to move?
    if mdx or mdy or drop or pickup:
        
        # we need to know the old contacts to test for collisions
        oldcontacts = contacts

        # determine contacts
        contacts = set()
        agentbody.build_contact_subtree(mdx, mdy, contacts)
        
        if pickup:
            holding = agentbody.self_and_all_pickable_neighbors()
        if drop:
            holding = set()
        
        contacts -= holding
        
        # check for collisions
        if oldcontacts != None and contacts != oldcontacts:
            # we've hit a new object; stop temporarily
            temp_stop = True

        # set sensors to indicate motion as appropriate
        if any([body.fixed for body in contacts]) or temp_stop:
            adx = 0
            ady = 0
        else:
            adx = mdx
            ady = mdy
            
        agentbody.x += adx
        agentbody.y += ady
        
        for body in holding:
            if body == agentbody: continue
            body.x += adx
            body.y += ady

        print contacts
        print "HOLDING", holding
    else:
        # agent has chosen to stop
        adx = ady = 0
        contacts = None
        temp_stop = False

# For a real agent, this would take the current sensor values and
# compute new effector values.  Since at present a human is playing
# the role of the agent, we use this subroutine as a place to process
# the human's commands.
def behave():
    global mdx, mdy, blind_mode, pickup, drop
    
    for event in pygame.event.get():
         if event.type == pygame.QUIT:
              pygame.quit(); sys.exit();
         elif event.type is pygame.MOUSEBUTTONDOWN:
             mdown = pygame.mouse.get_pos()
         elif event.type is pygame.MOUSEBUTTONUP:
             pass
         elif event.type is pygame.KEYDOWN and mdx == mdy == 0:
             if event.unicode == 'b':
                 blind_mode = not blind_mode
             if event.unicode == 'k':
                 mdy = -1
             if event.unicode == 'j':
                 mdy = 1
             if event.unicode == 'h':
                 mdx = -1
             if event.unicode == 'l':
                 mdx = 1
             if event.unicode == 'p':
                 pickup = 1
             if event.unicode == 'd':
                 drop = 1
             if event.unicode == 'q':
                 pygame.quit(); sys.exit();
         elif event.type is pygame.KEYUP:
             mdx = mdy = pickup = drop = 0


#############################################################
# main loop

while True:

    # step the simulation
    evolve_world()

    # redraw
    screen.fill(white)
    draw()
    pygame.display.update()

    # let the agent change its effector values
    behave()

    # print sensor and effector values
    format = "Timestep: %4s     Effectors: %2s %2s %s     Sensors: %2s %2s %s"
    print format  % (t,
                     mdx, mdy,
                     1 if magnetism else 0,
                     adx, ady,
                     " ".join([('1' if agentbody.neighbors(dx2,dy2) else '0')
                               for dx2, dy2 in cardinal_directions]))

    # delay to get a stable framerate
    clock.tick(60)
    t += 1
