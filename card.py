import log

def ranksym(rank):
    log.logger.debug('Card.ranksym()')
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
        log.logger.debug('Card.__init__()')
        self.cardnum = cardnum

    def __str__(self):
        log.logger.debug('Card.__str__()')
        return '[Card:%d:%s:%s]' % (self.cardnum, self.face(), self.cardname())

    def __cmp__(self, other):
        log.logger.debug('Card.__cmp__()')
        return cmp(self.rank(), other.rank())

    def rank(self):
        log.logger.debug('Card.rank()')
        return self.cardnum % 13

    def rankname(self):
        log.logger.debug('Card.rankname()')
        return self.ranks[self.rank()]

    def suit(self):
        log.logger.debug('Card.suit()')
        return self.cardnum / 13

    def suitname(self):
        log.logger.debug('Card.suitname()')
        return self.suits[self.suit()]

    def cardname(self):
        log.logger.debug('Card.cardname()')
        return self.rankname() + ' of ' + self.suitname()

    def face(self):
        log.logger.debug('Card.face()')
        return '%c%c' % (Card.facerank[self.rank()],
                         Card.facesuit[self.suit()])

if __name__ == '__main__':
    import random
    foo = Card(random.randrange(0, 52))
    bar = Card(random.randrange(0, 52))
    baz = Card(random.randrange(0, 52))
    for card in (foo, bar, baz):
        print card, card.face(), card.rank(), card.suit(), card.suitname()

    for c1 in (foo, bar, baz):
        for c2 in (foo, bar, baz):
            diff = cmp(c1, c2)
            if diff > 0:
                print '%s > %s' % (c1.face(), c2.face())
            elif diff < 0:
                print '%s < %s' % (c1.face(), c2.face())
            else:
                print '%s == %s' % (c1.face(), c2.face())
