import log

class Command:
    "Extracts protocol, id, command, and arg from mail filter input"

    def __init__(self, proto='EMAIL', plid='', cmd='NOOP', arg=''):
        log.logger.debug('Command.__init__()')

        self.proto = proto
        self.id = plid
        self.cmd = cmd
        self.arg = arg
    def __str__(self):
        log.logger.debug('Command.__str__()')

        return '[Command:%s:%s:%s:%s]' %\
               (self.proto, self.id, self.cmd, self.arg)
    def extractcmd(self, cmdstring):
        log.logger.debug('Command.extractcmd()')

        if cmdstring:
            try:
                self.proto, self.id, self.cmd, self.arg =\
                            cmdstring.strip().split(':', 3)
            except:
                log.logger.warning('Command.extractcmd(): bad command format: \'%s\'' % cmdstring)
                self.proto = 'EMAIL'
                self.id = ''
                self.cmd = 'NOOP'
                self.arg = ''
            self.cmd = self.cmd.upper()

            if self.cmd == 'CALL' and self.arg == 'MAXIMUM':
                self.cmd = 'CALLMAX'

    def goodarg(self):
        'Format Command.arg'

        goodarg = True;
        
        log.logger.debug('Command.goodarg()')

        intargcmds = ['BET', 'CALL', 'MAKE', 'RAISE', 'BLIND',
                      'DOUBLE', 'BANKROLL']

        txtargcmds = ['JOIN', 'WAIT', 'REMIND', 'PASSWORD']

        if self.cmd in intargcmds:

            log.logger.debug('Command:%s' % self)

            try:
                self.arg = int(self.arg)
            except:
                self.arg = ''
                if self.cmd == 'CALL':

                    log.logger.debug('Command:Setting cmd to CALLMAX')

                    self.cmd = 'CALLMAX'

                # In NLHE, BET/MAKE, RAISE must have arguments
                else:
                    goodarg = False

        elif self.cmd in txtargcmds:
            if not self.arg:
                goodarg = False

        return goodarg
            
if __name__ == '__main__':
    acommand = Command()
    print acommand
    acommand.extractcmd('EMAIL:abcdefgh:call:199')
    print acommand

    # this should fail
    acommand.extractcmd('IRC:abcdefgh:call')
    print acommand
