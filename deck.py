from random import random, seed, shuffle
from struct import unpack
from card import Card
import log

class Deck:
    '''
    A standard 52 card deck
    '''

    error = 'deck.error'
    def __init__(self):
        log.logger.debug('Deck.__init__()')

        self.cards = range(0, 52)
        self.topcard = -1
    def __str__(self):
        buf = ''
        for card in self.cards:
            buf += '%d ' % card
        return buf.strip()

    def reseed(self):
        log.logger.debug('Deck.reseed()')

        ef = open('/dev/random', 'r')
        entropy = ef.read(29)
        #seed(hash(entropy))
        seed(entropy)
    def shuffle(self, newdeck = False):
        'Shuffle using Random.shuffle()'

        log.logger.debug('Deck.shuffle()')

        # start from a fresh deck, if requested
        if newdeck:
            self.cards.sort()
        self.topcard = -1
        shuffle(self.cards)

    def shuffle2(self, newdeck = False):
        'Shuffle using Knuth shuffle algorithm and /dev/random'

        log.logger.debug('Deck.shuffle2()')
        
        # start from a fresh deck, if requested
        if newdeck:
            self.cards.sort()
        self.topcard = -1

        for i in xrange(51, -1, -1):
            rnum = self.rand51()
            temp = self.cards[rnum]
            self.cards[rnum] = self.cards[i]
            self.cards[i] = temp

    def rand51(self):
        '''Draw a random integer between 0 and 51 using /dev/(u)random
        It is possible to substitute random for urandom should the
        need arise for a "guarantee" of "randomness".'''

        log.logger.debug('Deck.rand51()')

        rf = open('/dev/urandom', 'r')
        while True:
            byte = rf.read(1)

            # Convert byte to an unsigned int and mask off 6 bits
            byte = unpack('B', byte)[0] & 63

            # Redraw if the masked byte is > 51, otherwise return it
            if byte <= 51:
                rf.close()
                break
            else:
                continue

        return byte

    def nextcard(self):
        log.logger.debug('Deck.nextcard()')

        if self.topcard == 51:
            raise Deck.error, 'no cards left in deck'
        self.topcard += 1
        return Card(self.cards[self.topcard])

if __name__ == '__main__':
    foo = Deck()
    #foo.reseed()
    for i in xrange(0, 10):
        print '-------------------------------'
        foo.shuffle2(True)
        for card in xrange(0,52):
            print foo.nextcard().face(),
            if not (card + 1) % 13:
                print

