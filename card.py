#
#    Copyright (C) 2004 Paul Rotering
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA
import log

def ranksym(rank):
    #log.logger.debug('Card.ranksym()')
    return Card.facerank[rank]

class Card:
    '''
    A standard playing card
    '''

    ranks = ('deuce', 'trey', 'four', 'five', 'six', 'seven', 'eight',
             'nine', 'ten', 'jack', 'queen', 'king', 'ace')
    suits = ('clubs', 'diamonds', 'hearts', 'spades')
    facerank = ('2', '3', '4', '5', '6', '7', '8',
                '9', 'T', 'J', 'Q', 'K', 'A')
    facesuit = ('c', 'd', 'h', 's')
    def __init__(self, cardnum=0):
        #log.logger.debug('Card.__init__()')
        self.cardnum = cardnum

    def __str__(self):
        #log.logger.debug('Card.__str__()')
        return '[Card:%d:%s:%s]' % (self.cardnum, self.face(), self.cardname())

    def __cmp__(self, other):
        #log.logger.debug('Card.__cmp__()')
        return cmp(self.rank(), other.rank())

    def rank(self):
        #log.logger.debug('Card.rank()')
        return self.cardnum % 13

    def rankname(self):
        #log.logger.debug('Card.rankname()')
        return self.ranks[self.rank()]

    def suit(self):
        #log.logger.debug('Card.suit()')
        return self.cardnum / 13

    def suitname(self):
        #log.logger.debug('Card.suitname()')
        return self.suits[self.suit()]

    def cardname(self):
        #log.logger.debug('Card.cardname()')
        return self.rankname() + ' of ' + self.suitname()

    def face(self, color = False):
        #log.logger.debug('Card.face()')

        r = Card.facerank[self.rank()]
        s = Card.facesuit[self.suit()]
        f = r + s

	#color = False

        if color:
            if s == 'c':
                f = '03,00%c%c' % (r, s)
                #f = '\033[47m\033[32m%c%c\033[0;0m' % (r, s)
            elif s == 'd':
                f = '02,00%c%c' % (r, s)
                #f = '\033[47m\033[34m%c%c\033[0;0m' % (r, s)
            elif s == 'h':
                f = '04,00%c%c' % (r, s)
                #f = '\033[47m\033[31m%c%c\033[0;0m' % (r, s)
            elif s == 's':
                f = '01,00%c%c' % (r, s)
                #f = '\033[47m\033[30m%c%c\033[0;0m' % (r, s)
                         
        return f

if __name__ == '__main__':
    import random
    foo = Card(random.randrange(0, 52))
    bar = Card(random.randrange(0, 52))
    baz = Card(random.randrange(0, 52))
    for card in (foo, bar, baz):
        print card, card.face(True), card.rank(), card.suit(), card.suitname()

    for c1 in (foo, bar, baz):
        for c2 in (foo, bar, baz):
            diff = cmp(c1, c2)
            if diff > 0:
                print '%s > %s' % (c1.face(True), c2.face(True))
            elif diff < 0:
                print '%s < %s' % (c1.face(True), c2.face(True))
            else:
                print '%s == %s' % (c1.face(True), c2.face(True))
