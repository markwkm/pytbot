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
import sys
from datetime import datetime

from command import Command
from deck import Deck
from player import Player
from pot import Pot

class Tourney:
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3
    nholecards = 2
    nboardcards = 5

    def __init__(self, tnum = 0, pubout=None, privout=None, noteout = None):
        log.logger.debug('Tourney.__init__()')

        self.tnum = tnum
        self.pubout = pubout
        self.privout = privout
        self.noteout = noteout
        self.maxplayers = 23
        self.nstartplayers = 0
        self.players = []
        self.waiters = []
        self.playing = False
        self.aborted = False
        self.ante = 0
        self.loblind = 10
        self.hiblind = 20
        self.bankroll = 1000
        self.maxbankroll = 434000 # br needs to fit in 7 spaces
        self.blindinterval = 300
        self.handnum = 0
        self.handsflag = False
        self.handsinterval = 0
        self.bb = 0
        self.sb = 0
        self.button = 0
        self.next2act = 0
        self.nosb = False
        self.butflag = False
        self.bbacted = False
        self.curbet = 0
        self.minraise = 0
        self.pot = 0
        self.pots = []
        self.lastbettor = 0
        self.round = 0
        self.players = []
        self.board = []
        self.activelist = []
        self.deck = Deck()

        self.dt = datetime(2000, 1, 1)
        self.timestamp = self.dt.now()


        self.buildpasswd()
        
    def buildpasswd(self):

        # Load password file
        self.passwdfile = 'passwd.lst'
        self.passwd = {}
        try:
            pfile = file(self.passwdfile, 'r')
        except IOError, (errno, strerror):
            log.logger.critical("Problem loading password file %s:%s" %\
                  (self.passwdfile, strerror))
            print "Problem loading password file %s:%s" %\
                  (self.passwdfile, strerror)
            sys.exit(1)
        
        nplayers = 0
        for line in pfile:
            nplayers += 1
            name, pswd = line.split(':')
            pswd = pswd.strip()
            self.passwd[name] = pswd
        
        pfile.close()
        
        log.logger.info('%d player passwords loaded' % nplayers)

    def replacepasswd(self, name, newpswd):
        import os

        log.logger.debug('Tourney.replacepasswd()')

        log.logger.info('Tourney.replacepasswd: replacing password for %s:(%s)' % (name, newpswd))

        success = True

        try:

            nfname = os.tempnam('.')
            nfile = file(nfname, 'w')
            pfile = file(self.passwdfile, 'r')
            for line in pfile:
                (n, p) = line.split(':')
                if n == name:
                    nfile.write('%s:%s\n' % (name, newpswd))
                else:
                    nfile.write(line)

            nfile.flush()

            pfile.close()
            nfile.close()
        except IOError, (errno, strerror):
            log.logger.critical("Tourney.replacepasswd:Problem replacing password")
            print 'Problem replacing password'
            success = False

        if success:
            os.rename(nfname, self.passwdfile)

        self.buildpasswd()
        

    def save1passwd(self, name, pswd):
        '''Add a new player to the password file.  Assumes that the
        player name is actually new.'''

        log.logger.debug('Tourney.save1passwd()')
        print 'Tourney.save1passwd:Adding new player %s' % name
        log.logger.info('Tourney.save1passwd:Adding new player %s' % name)
        
        success = True

        try:
            pfile = file(self.passwdfile, 'a+')
            pfile.write('%s:%s\n' % (name, pswd))
            pfile.flush()
            pfile.close()
        except IOError, (errno, strerror):
            log.logger.critical("Tourney.save1passwd:Problem saving password")
            print 'Problem saving password'
            success = False
        
        return success

    def incmd(self, cmd):
        log.logger.debug('Tourney.incmd()')

        log.logger.debug('Tourney.incmd:%s' % cmd)

        actions = ['BET', 'CALL', 'CALLMAX', 'CHECK', 'FOLD', 'MAKE',
        'RAISE', 'UNDO', 'JAM', 'POT']
        
        gamecmds = actions + ['ABORT', 'BACK', 'CARDS', 'KICK',
        'VACATION', 'REMIND', 'QUIT', 'PASSWORD']

        setupcmds = ['DOUBLE', 'BANKROLL', 'BLIND', 'START']
        
        run = False

        c = cmd.cmd
        p = self.pfromnick(cmd.id)
        pid = cmd.id

        if (c in gamecmds or c in setupcmds) and p == None:
            self.noteout(pid, 'You must be in the game to use the %s command.' % cmd.cmd)

        elif c in actions and p.allin:
            self.noteout(pid, "You're all in.  Command ignored.")
        
        elif c in actions and p.folded:
            self.noteout(pid, "You're not involved in this hand.  %s command ignored." % c)

        elif c in gamecmds and not self.playing:
            if c == 'PASSWORD':
                self.replacepasswd(pid, cmd.arg)
                self.privout(pid, 'Password replaced with %s' % cmd.arg)

            elif c == 'QUIT':
                msg = '%s has quit.  We now have %d player' %\
                      (pid, len(self.players) - 1)
                self.players.remove(p)
                if len(self.players) > 1:
                    msg += 's '
                else:
                    msg += ' '
                msg += 'in the tournament.'
                self.pubout(msg)

                #####if len(self.waiters) > 0:
                #####    (nick, pswd) = self.waiters.pop(0)
                #####    self.joingame(nick, pswd)

            else:
                self.privout(pid, 'There is currently no game.  %s command ignored.' % c)
                
        elif c in setupcmds and self.playing:
            self.privout(pid, "%s can't be used while a game is being played." % cmd.cmd)

        elif c == 'HELP' or c == 'COMMANDS':
            self.dohelp(pid)

        elif c == 'JOIN':
            if self.ingame(pid):
                self.privout(pid, "You're already in the game.")
            elif self.playing:
                #self.privout(pid, "Sorry, there's a tournament already in progress.  Use 'wait <passwd>' to get on the waiting list for the next tournament.")
                self.privout(pid, "Sorry, there's a tournament already in progress.")
            else:
                if len(self.players) == self.maxplayers:
                   #self.privout(pid, "Sorry, the table is full.  Use 'wait <passwd>' to get on the waiting list for the next tournament.")
                   self.privout(pid, "Sorry, the table is full.")

                # valid JOIN command
                else:
                    self.joingame(pid, cmd.arg)
        
        elif c == 'STATUS':
            self.prettyprint(pid)

        elif c == 'ABORT':
            self.pubout('%s has aborted the tournament!  Please finish this hand.' % pid)
            self.aborted = True
            run = True

        #####elif c == 'UNWAIT':
        #####    inwaiters = False
        #####    for n, pswd in self.waiters:
        #####        if n == pid:
        #####            inwaiters = True
        #####            break
        #####    if self.ingame(pid) or not inwaiters:
        #####        self.privout(pid, "You're not on the waiting list.")

        #####elif c == 'WAIT':
        #####    if self.ingame(pid):
        #####        self.privout(pid, "You're already in the game.")
        #####    else:
        #####        inwaiters = False
        #####        for n, pswd in self.waiters:
        #####            if n == pid:
        #####                inwaiters = True
        #####                break
        #####            if inwaiters:
        #####                self.privout(pid, "You're already on the waiting list.")
        #####            elif not self.playing and len(self.players) < self.maxplayers:
        #####                self.privout(pid, "There's room at the table.  Please use join.")
        #####            else:
        #####                self.waiters.append((pid, cmd.arg))
        #####                nwaiters = 0
        #####                for n, pswd in self.waiters:
        #####                    nwaiters += 1
        #####                    if n == pid:
        #####                        self.noteout(pid, "Added to waiting list.  You're #%d on the list." % nwaiters)
        #####                        break

        elif c == 'BOARD':
            if not self.playing:
                self.privout(pid, 'There is currently no board to display.')
            else:
                self.noteout(pid, 'Board:      %s' % self.printboard(self.round))
                
        elif c == 'BLIND':
            self.loblind = cmd.arg
            self.hiblind = 2 * self.loblind
            self.pubout('%s set the blinds to %s-%s' %\
                        (pid, self.loblind, self.hiblind))

        elif c == 'BANKROLL':
            self.bankroll = cmd.arg
            if self.bankroll > self.maxbankroll:
                self.bankroll = self.maxbankroll
            self.pubout('%s set the initial bankroll to $%d' %\
                        (cmd.id, self.bankroll))

        elif c == 'DOUBLE':
            msg = ('%s set the doubling interval to %s' % (pid, cmd.arg))
            if self.handsflag:
                self.handsflag = False
                self.handsinterval = cmd.arg
                msg += ' hands.'
            else:
                self.blindinterval = cmd.arg
                msg += ' seconds.'

            self.pubout(msg)

        elif c == 'START':
            if len(self.players) < 2:
                self.noteout(pid, 'I need at least two players to start a tournament.')
            else:
                self.playing = True
                self.pubout('A new tourney is about to begin.  Good luck!')
                self.begin()

        elif c == 'ABORT':
            self.pubout('Tourney aborted by %s.  Finishing hand' % pid)
            self.aborted = True

        elif c == 'CARDS':
            self.noteout(pid, 'Your hole cards are: %s %s' %\
                         (p.hand.cards[0].face(),
                          p.hand.cards[1].face()))

        elif c == 'BACK':
            if not p.vacation:
                self.noteout(pid, "You're not on vacation.  Command ignored.")
            else:
                p.vacation = False
                p.cmd.cmd = 'NOOP'
                p.cmd.arg = ''
                self.pubout('%s is back from vacation!' % pid)

        elif c == 'VACATION':
            if cmd.arg == '':
                cmd.arg = pid
            player = None
            player = self.pfromnick(cmd.arg)
            if player:
                if not player.vacation:
                    self.pubout('%s has sent %s on vacation!' % (p.nick, player.nick))
                    player.vacation = True
                    player.cmd.cmd = 'FOLD'
                    player.cmd.arg = ''
                    run = True

        elif c == 'UNDO':
            p.cmd.cmd = 'NOOP'
            p.cmd.arg = ''
            self.noteout(pid, 'Advance action cancelled.')
        
        elif c == 'QUIT':
            if p.quit:
                self.privout(pid, "You've already quit!")                
            else:
                self.privout(pid, "Okay, you're gone!")
                p.cmd.cmd = 'FOLD'
                p.cmd.arg = ''
                p.quit = True
                if (self.players.index(p) == self.next2act) or\
                       (self.nlive() - self.nquitters() == 1):
                    run = True
            
        elif c == 'REMIND':
            bugee = self.players[self.next2act].nick
            if bugee.upper() != cmd.arg.upper():
                player = self.pfromnick(cmd.arg)
                if not player:
                    self.privout(pid, "%s isn't in the tournament!" %\
                                 cmd.arg)
                else:
                    self.privout(pid, "It's not %s's turn to act!" %\
                                 player.nick)
            else:
                self.privout(bugee, "%s reminds you that it's your turn to act." % pid)

        elif c in actions:
            p.cmd = cmd
            if self.players.index(p) == self.next2act:
                run = True

        if self.playing and run:
            self.run()

    def joingame(self, nick, pswd):
    
        goodjoin = True

        # Add new players to Tourney.passwd
        if not nick in self.passwd:
            self.passwd[nick] = pswd
            self.save1passwd(nick, pswd)
                    
        # Check for valid password
        elif pswd != self.passwd[nick]:
            self.privout(nick, "Invalid password.  Please try joining again.")
            goodjoin = False
                    
        if goodjoin:
            self.players.append(Player(nick, nick))
            self.noteout(nick, 'Welcome to the game.')
            msg = ('%s has joined the game.  We now have %d player' %\
                   (nick, len(self.players)))
            if len(self.players) > 1:
                msg += 's '
            else:
                msg += ' '
            msg += 'in the tournament.'
            self.pubout(msg)
    
    def run(self):
        log.logger.debug('Tourney.run()')

        p = self.players[self.next2act]

        sendstatus = True

        # If at least two players do some kind of action, make sure a
        # broadcast message is sent even if the last action fails.
        niterations = 0

        while p.cmd.cmd != 'NOOP':

            niterations += 1
            tocall = self.curbet - p.action

            # Fold at the earliest opportunity.  Check if there's no bet.
            if p.cmd.cmd == 'FOLD':

                if p.action >= self.curbet:
                    if p.vacation:
                        log.logger.info('Tourney.run:%s is on vacation and checks' % p.nick)
                    else:
                        log.logger.info('Tourney.run:%s checks' % p.nick)
                    self.pubout('%s checks.' % p.nick)
                    p.cmd.cmd = 'FOLD'
                else:
                    p.folded = True
                    p.cmd.cmd = 'NOOP'
                    nactive = self.nactive()
                    msg = '%s folds.  We now have %d player' %\
                          (p.nick, nactive)
                    if nactive > 1:
                        msg += 's in the hand.'
                    else:
                        msg += ' in the hand.'
                    self.pubout(msg)
                    if p.vacation:
                        log.logger.info('Tourney.run:%s is on vacation and folds' % p.nick)
                    else:
                        log.logger.info('Tourney.run:%s folds' % p.nick)

            elif p.cmd.cmd == 'CALL':

                # call $0 == check if no bet
                if tocall == 0:
                    p.cmd.cmd = 'CHECK'
                    p.cmd.arg = ''
                    niterations -= 1
                    continue
                else:

                    # call $0 == fold if there's a bet
                    if p.cmd.arg ==  0:
                        p.cmd.cmd = 'FOLD'
                        p.cmd.arg = ''
                        niterations -= 1
                        continue

                    # regular call
                    else:
                        advseat = self.CALL(p)
                        if not advseat:
                            if p.cmd.cmd == 'FOLD':
                                niterations -= 1
                                continue
                            sendstatus = False
                            break

            # Call any bet
            elif p.cmd.cmd == 'CALLMAX':

                # Call $0 == check
                if tocall == 0:
                    p.cmd.cmd = 'CHECK'
                    p.cmd.arg = ''
                    niterations -= 1
                    continue

                else:
                    self.CALLMAX(p)

            elif p.cmd.cmd == 'RAISE':
                advseat = self.RAISE(p)
                if not advseat:
                    sendstatus = False
                    break

            elif p.cmd.cmd == 'JAM':
                p.cmd.cmd = 'BET'
                p.cmd.arg = p.bankroll + p.action
                niterations -= 1
                continue

            elif p.cmd.cmd == 'BET' or p.cmd.cmd == 'MAKE':
                tomake = int(p.cmd.arg)


                if tomake < tocall:
                    self.privout(p.nick,
                                 'Insufficient bet: minimum to call is $%d' %\
                                 (tocall,))
                    log.logger.debug('Tourney.run:%s call is too small' %\
                                     (p.nick,))

                    # Don't advance seat
                    advseat = False
                    p.cmd.cmd = 'NOOP'
                    p.cmd.arg = ''

                    break

                elif tomake == tocall:
                    p.cmd.cmd = 'CALL'
                    p.cmd.arg = tomake
                    niterations -= 1
                    continue
                if tomake > tocall:
                    p.cmd.cmd = 'RAISE'
                    p.cmd.arg = tomake - tocall - p.action
                    niterations -= 1
                    continue
            
            elif p.cmd.cmd == 'CHECK':

                p.cmd.cmd = 'NOOP'

                if tocall == 0:
                    self.pubout('%s checks.' % p.nick)
                    log.logger.info('Tourney.run:%s checks' % p.nick)
                else:
                    log.logger.info('Tourney.run:%s check when $%d to call' %\
                                    (p.nick, tocall))

                    self.privout(p.nick, 'Insufficient bet: $%d to call' %\
                                 tocall)
                    sendstatus = False
                    break

            # Attempt to bet the value of the pot.  If player's bankroll
            # is less than pot, go all in.
            elif p.cmd.cmd == 'POT':
                p.cmd.cmd = 'BET'
                p.cmd.arg = self.pot + tocall
                niterations -= 1
                continue

            else:
                log.logger.critical('Tourney.run: unknown command %s' %\
                                    p.cmd.cmd)
                sendstatus = False
                break

            self.buildactivelist()
            nactive = len(self.activelist)

            # End of hand if only one active player
            if nactive == 1:
                self.endhand()
                if not self.playing:
                    return
                self.newhand()
                return

            allin = True;
            while allin:
                self.next2act = self.nextactiveseat()
                p = self.players[self.next2act]

                # End of round if next player is last bettor
                if self.next2act == self.lastbettor:

                    # Unless it's preflop and we've limped to the big blind
                    if self.round == Tourney.PREFLOP and \
                           self.next2act == self.bb and not self.bbacted:
                        
                        self.lastbettor = self.nextactiveseat(self.bb)
                        self.bbacted = True
                    else:

                        log.logger.info('Tourney.run: Betting round over - go to next round')
                        self.makepots()
                        self.nextround()
                        return

                if not p.allin:
                    allin = False


        # All but one player has quit.  He wins.
        if self.nlive() - self.nquitters() == 1:
            self.endhand(False)

        else:

            self.makepots()

            if sendstatus or niterations > 1:
                log.logger.debug('Tourney.run:%s is next to act. (%d to call)' %(self.players[self.next2act].nick, self.curbet - self.players[self.next2act].action))
            
                self.pubout('%s is next to act. (%d to call)' %\
                            (self.players[self.next2act].nick,
                             self.curbet - self.players[self.next2act].action))
            
    def CALL(self, p):
        log.logger.debug('Tourney.CALL()')
         
        advseat = True

        tocall = self.curbet - p.action

        if p.cmd.arg == 'MAXIMUM':
            arg = tocall
        else:
            try:
                arg = int(p.cmd.arg)
            except:
                arg = tocall

        if arg < tocall:
            if p.bankroll > arg:

                # Don't advance seat and FOLD
                advseat = False
                p.cmd.cmd = 'FOLD'
                p.cmd.arg = ''

            # All-in call
            else:
                self.pot += p.bankroll
                p.action += p.bankroll
                p.inplay += p.bankroll
                p.lastbet = self.curbet

                p.allin = True;
                self.sidepots = True

                self.pubout('%s calls $%d - side pot.  Pot is now $%d.' %\
                            (p.nick, p.bankroll, self.pot))

                p.bankroll = 0
                log.logger.info('Tourney.CALL:%s calls - side pot' % p.nick)

        elif arg >= tocall:

            # Normal call
            p.lastbet = self.curbet
            if tocall < p.bankroll:
                self.pot += tocall
                p.action += tocall
                p.inplay += tocall
                p.bankroll -= tocall

                self.pubout('%s calls $%d.  Pot is now $%d.' %\
                                   (p.nick, tocall, self.pot))
                log.logger.info('Tourney.CALL:%s calls' % p.nick)

            # All-in call
            elif tocall >= p.bankroll:
                self.pot += p.bankroll
                p.action += p.bankroll
                p.inplay += p.bankroll

                p.allin = True

                if tocall == p.bankroll:
                    self.pubout('%s calls $%d and is all in.  Pot is now $%d.' % (p.nick, tocall, self.pot))
                    log.logger.info('Tourney.CALL:%s calls' % p.nick)

                                
                else:
                    self.sidepots = True
   
                    self.pubout('%s calls $%d - side pot.  Pot is now $%d.' %\
                                (p.nick, p.bankroll, self.pot))
                    log.logger.info('Tourney.CALL:%s calls - side pot' %\
                                    p.nick)

                p.bankroll = 0

        if p.cmd.cmd != 'FOLD':
            p.cmd.cmd = 'NOOP'
            p.cmd.arg = ''

        return advseat

    def CALLMAX(self, p):
        log.logger.debug('Tourney.CALLMAX()')

        tocall = self.curbet - p.action

        # All-in call
        if p.bankroll < tocall:
            self.pot += p.bankroll
            p.action += p.bankroll
            p.inplay += p.bankroll

            p.allin = True
            self.sidepots = True

            self.pubout('%s calls $%d - side pot.  Pot is now $%d.' %\
                               (p.nick, p.bankroll, self.pot))
            log.logger.info('Tourney.CALLMAX:%s calls - side pot' % p.nick)

            p.bankroll = 0

        else:
            p.lastbet = self.curbet
            self.pot += tocall
            p.action += tocall
            p.inplay += tocall
            if tocall == p.bankroll:
                p.allin = True
            p.bankroll -= tocall

            self.pubout('%s calls $%d.  Pot is now $%d.' %\
                        (p.nick, tocall, self.pot))
            log.logger.info('Tourney.CALLMAX:%s calls' % p.nick)
        
        p.cmd.cmd = 'NOOP'
        p.cmd.arg = ''

    def RAISE(self, p):
        log.logger.debug('Tourney.RAISE()')

        advseat = True
        araise = p.cmd.arg
        tocall = self.curbet - p.action

        log.logger.debug('----------------------------------------')
        log.logger.debug('%s raising' % p.nick)
        log.logger.debug('       table.curbet = $%d' % self.curbet)
        log.logger.debug('     table.minraise = $%d' % self.minraise)
        log.logger.debug('     player.lastbet = $%d' % p.lastbet)
        log.logger.debug('    player.bankroll = $%d' % p.bankroll)
        log.logger.debug('      player.inplay = $%d' % p.inplay)
        log.logger.debug('      player.action = $%d' % p.action)
        log.logger.debug('              raise = $%d' % araise)
        log.logger.debug('             tocall = $%d' % tocall)
        log.logger.debug('----------------------------------------')

        # 'raise $0' calls any bet
        if araise == 0:
            p.cmd.cmd = 'CALLMAX'
            advseat = False

        # Check to see if player was fully raised
        elif (self.curbet == 0) or (self.curbet - self.minraise >= p.lastbet):

            # OK to raise

            # Raise too small?
            if araise < self.minraise:

                # All-in raise?
                if tocall + self.minraise > p.bankroll:
                    if self.nallin() > 0: self.sidepots = True;
                    self.lastbettor = self.players.index(p)
                    self.pot += p.bankroll
                    p.action += p.bankroll
                    p.inplay += p.bankroll
                    p.lastbet = p.action

                    log.logger.debug('Tourney.RAISE:Setting self.curbet to $%d' % p.action)

                    self.curbet = p.action

                    self.minraise += p.bankroll - tocall

                    self.pubout('%s raises $%d and is all in.  Pot is now $%d.' % (p.nick, p.bankroll - tocall, self.pot))
                    log.logger.info('Tourney.RAISE: %s raises $%d and is all in' % (p.nick, p.bankroll - tocall))

                    p.bankroll = 0
                    p.allin = True

                else:

                    # Raise too small
                    log.logger.info('Tourney.RAISE: %s raised $%d when minraise $%d' % (p.nick, araise, self.minraise))

                    if tocall == 0:
                        self.privout(p.nick, 'Insufficient bet.  Minimum bet is $%d' % self.minraise)
                    else:
                        self.privout(p.nick, 'Insufficient raise.  Minimum raise is $%d' % self.minraise)

                    # Don't advance seat
                    advseat = False

            else:

                # Raise >= minimum raise
                if self.curbet == 0:
                    chips = araise
                else:
                    chips = self.curbet - p.action + araise
                
                if p.bankroll <= tocall:

                    # Not enough chips for the given raise
                    log.logger.info('Tourney.RAISE: %s attempted to raise with insufficient chips to call' % p.nick)

                    self.privout(p.nick, 'Insufficient chips to raise.  Please CALL or FOLD')
                    # Don't advance seat
                    advseat = False

                # All-in raise
                elif tocall < p.bankroll <= chips:
                    if self.nallin() > 0: self.sidepots = True;
                    self.lastbettor = self.players.index(p)
                    self.pot += p.bankroll
                    p.action += p.bankroll
                    p.inplay += p.bankroll
                    p.lastbet = p.action
                    if self.curbet == 0:
                        
                        self.pubout('%s bets $%d and is all in.  Pot is now $%d.' % (p.nick, p.bankroll, self.pot))
                        log.logger.info('Tourney.RAISE: %s bet $%d and is all in' % (p.nick, p.bankroll))
                    else:

                        self.pubout('%s raises $%d and is all in.  Pot is now $%d.' % (p.nick, p.bankroll - tocall, self.pot))
                        log.logger.info('Tourney.RAISE: %s raises $%d and is all in' % (p.nick, p.bankroll - tocall))

                    p.allin = True
                    self.curbet = p.action
                    self.minraise = self.curbet - self.minraise
                    p.bankroll = 0

                # Normal raise
                else:
                    if self.nallin() > 0: self.sidepots = True;
                    self.lastbettor = self.players.index(p)
                    self.pot += chips
                    p.action += chips
                    p.inplay += chips
                    p.lastbet = self.curbet + araise
                    p.bankroll -= chips
                    if self.curbet > 0:
                        self.pubout('%s raises $%d.  Pot is now $%d.' %\
                                    (p.nick, araise, self.pot))
                        log.logger.info('Tourney.RAISE:%s raises $%d' %\
                                        (p.nick, araise))
                    else:
                        log.logger.debug('Tourney.RAISE:chips = $%d' % chips)
                        self.pubout('%s bets $%d.  Pot is now $%d.' %\
                                    (p.nick, araise, self.pot))
                        log.logger.info('Tourney.RAISE:%s bets $%d' %\
                                        (p.nick, araise))
                    self.curbet += araise
                    self.minraise = araise

        else:
            log.logger.info('Tourney.RAISE:%s raises when not fully raised' %\
                            p.nick)
            self.privout(p.nick, 'You were not fully raised and cannot raise.  Plase call or fold.')

            # Don't advance seat
            advseat = False

        # Clear command if it hasn't been changed
        if p.cmd.cmd == 'RAISE':
            p.cmd.cmd = 'NOOP'

        return advseat

    def ingame(self, pid):
        log.logger.debug('Tourney.ingame()')

        result = False

        for p in self.players:
            if p.myid == pid:
                result = True
                break

        return result

    def prettyprint(self, pid):
        log.logger.debug('Tourney.prettyprint()')

        dealvac = ''
        status = ''

        self.noteout(pid, '+-+-----------------------+--------+--------+------+----+--------+')
        self.noteout(pid, '|#|   Name                |Bankroll| Action |Status|Pot#|Pot Size|')
        self.noteout(pid, '+-+-----------------------+--------+--------+------+----+--------+')
        for p in self.players:
            if p.busted:
                continue
            elif p.folded:
                status = 'FOLDED'
            elif p.quit:
                status = '<QUIT>'
            elif p.allin:
                status = 'all-in'
            if p.vacation:
                status = '<GONE>'
                if self.button == self.players.index(p):
                    dealvac = 'DV '
                else:
                    dealvac = 'V  '
            elif self.button == self.players.index(p):
                if self.next2act == self.players.index(p):
                    dealvac = 'D> '
                else:
                    dealvac = 'D  '
            elif self.next2act == self.players.index(p):
                dealvac = '>  '
            msg = '%2d|%3s%-20s|%8d|%8d|%6s' % (self.players.index(p) + 1, dealvac, p.nick, int(p.bankroll), int(p.inplay), status)

            if hasattr(self, 'sidepots'):
                if p.folded:
                    msg += '|    |        |'
                else:

                    # Find the least populated pot in which this
                    # player is involved
                    for pot in self.pots:
                        if pot.inpot(p):
                            break
                        msg += '| %2d |%8d|' % (len(pot.players), pot.value)
                    
            else:
                msg += '|    |        |'
            
            self.noteout(pid, msg)
            dealvac = ''
            status = ''
        self.noteout(pid, '+-+-----------------------+--------+--------+------+----+--------+')

    def printboard(self, nround):
        buf = ''
        if nround == Tourney.PREFLOP:
             buf += ''
        if nround == Tourney.FLOP:
            for n in xrange(3):
                buf += self.board[n].face() + ' '
        if nround == Tourney.TURN:
            for n in xrange(4):
                buf += self.board[n].face() + ' '
        if nround == Tourney.RIVER:
            for n in xrange(5):
                buf +=  self.board[n].face() + ' '
        return buf

    def pfromnick(self, nick):
        result = None

        for p in self.players:

            if p.nick.upper() == nick.upper():
                result = p
                break

        return result

    def activeplayers(self):
        log.logger.debug('Tourney.activeplayers()')

        liszt = []
        for p in self.players:
            if p.active():
                liszt.append(p)
        return liszt

    def buildactivelist(self):
        'Build an ordered list of active players for the current betting round'

        log.logger.debug('Tourney.buildactivelist()')

        self.activelist = []

        nplayers = len(self.players)
        for offset in xrange(nplayers):
            seat = (self.next2act + offset) % nplayers
            p = self.players[seat]
            if p.active():
                self.activelist.append(p)

    def endhand(self, showdown = True):
        log.logger.debug('Tourney.endhand()')

        if showdown:
            self.makepots()
            self.showdown()

        quitters = []
        for p in self.players:
            if not p.busted:
                if p.bankroll == 0:
                    log.logger.info('Tourney.endhand: Player %s eliminated' %\
                                    p.nick)

                    self.pubout('%s is busted!' % p.nick)
                    #p.busted = True
                    p.quit = True
            if p.quit:
                self.pubout('%s has quit' % p.nick)
                quitters.append(p)

        if len(quitters) > 0:
            quitters.sort(Player.oldbrsort)

            place = self.nlive()
            for q in quitters:
                msg = '%s finished #%d out of %d.  %d player' %\
                      (q.nick, place, self.nstartplayers, place - 1)
                if place - 1 > 1:
                    msg += 's remain.'
                else:
                    msg += ' remains.'
                self.pubout(msg)
                place -= 1
                q.busted = True
                q.quit = False
                self.players.remove(q)

        if self.tourneyover():
            self.endtourney()

    def showdown(self):
        from hand import Hand

        log.logger.debug('Tourney.showdown()')

        active = self.activeplayers()

        if len(active) == 1:

            active[0].bankroll += self.pot
            log.logger.info('%s wins $%d' % (active[0].nick, self.pot))

            self.pubout('%s wins $%d.' % (active[0].nick, self.pot))
        else:

            # Compare hands and award pots
            log.logger.info('Hand over, current board is: %s' %\
                            self.printboard(self.round))
            self.pubout('Board:      %s' % self.printboard(self.round))
            self.pubout("Players' hands:")
            self.showhands()

            for pot in self.pots:
                winners = pot.award()
                nwinners = len(winners)
                share = pot.value / nwinners
                leftovers = pot.value % nwinners

                log.logger.debug('pot %d: %d winners $%d share %d odd chips' %\
                      (self.pots.index(pot), nwinners, share, leftovers))

                # Sort winners for odd chip distribution
                if leftovers and nwinners > 1:
                    log.logger.debug('Distributing odd chips')
                    wseatorder = winners[:]
                    sorted = self.winseatsort(wseatorder)
                    
                for w in winners:
                    
                    myshare = share

                    # Distribute odd chip
                    if leftovers and w in sorted and \
                           (sorted.index(w) < leftovers):
                        log.logger.debug('%s gets extra chip' % w.nick)
                        myshare = share + 1

                    w.bankroll += myshare

                    if len(self.pots) == 1:

                        log.logger.info('%s wins $%d with %s %s' %\
                                        (w.nick, myshare,
                                         Hand.TYPE_STR[w.hand.type],
                                         w.hand.rankorderstr()))
                        self.pubout('High: %s wins $%d with %s %s' %\
                                    (w.nick, myshare,
                                     Hand.TYPE_STR[w.hand.type],
                                     w.hand.rankorderstr()))
                    else:

                        # print 'return uncalled foo' for a pot with a
                        # single payer
                        if len(pot.players) == 1:
                            log.logger.info('Pot %d: uncalled $%d returned to %s' % (len(pot.players), pot.value, w.nick))
                            self.pubout('%s wins $%d' % (w.nick, pot.value))
                        else:
                            log.logger.info('Pot %d: %s wins $%d with %s %s' % (len(pot.players), w.nick, myshare, Hand.TYPE_STR[w.hand.type], w.hand.rankorderstr()))
                            self.pubout('%s wins $%d with %s %s' %\
                                        (w.nick, myshare,
                                         Hand.TYPE_STR[w.hand.type],
                                         w.hand.rankorderstr()))

        #return active

    def showhands(self):
        log.logger.debug('Tourney.showhands()')
        
        first = self.nextactiveseat(self.lastbettor)
        next = -99
        aseat = first
        while next != first:
            log.logger.info('%-16s: %s' %\
                            (self.players[aseat].nick,
                             self.players[aseat].hand.showhole()))
            self.pubout('%-16s: %s' % (self.players[aseat].nick,
                                         self.players[aseat].hand.showhole()))
 
            self.fillhand(self.players[aseat])
            last = aseat
            aseat = self.nextactiveseat(last)
            next = aseat

    def fillhand(self, player):
        log.logger.debug('Tourney.fillhand()')

        for card in self.board:
            player.hand.addcard(card)

    def nextactiveseat(self, seat=-1):
        '''Return the seat number of the player who will be next to
        act after the current active player.
        
        An optional argument allows you to get the player who will be
        next to act after an arbitrary seat, specified by an integer
        seat number.'''

        log.logger.debug('Tourney.nextactiveseat()')

        if seat >= 0:
            oldas = seat
        else:
            oldas = self.next2act
        nplayers = len(self.players)
        for offset in xrange(1, nplayers):
            newas = (oldas + offset) % nplayers 
            if(not self.players[newas].folded and
               not self.players[newas].busted):
                return newas
        return oldas

    def tourneyover(self): return self.nlive() == 1

    def endtourney(self, abort = False):
        log.logger.debug('Tourney.endtourney()')        

        if not abort:
            plist = self.activeplayers()

            if len(plist) > 1:
                log.logger.critical('Tourney.endtourney called with > 1 active player!')

            else:
                self.pubout('The tourney is over.  %s wins!  Congratulations!' %plist[0].nick)
                log.logger.info('Tourney.endtourney: Tourney over, %s wins' % plist[0].nick)

        else:
            log.logger.info('Tourney.endtourney: Tourney aborted!')

        self.playing = False

        self.ante = 0
        self.loblind = 10
        self.hiblind = 20
        self.bankroll = 1000
        self.maxbankroll = 434000 # br needs to fit in 7 spaces
        self.blindinterval = 300
        self.handnum = 0
        self.handsflag = False
        self.handsinterval = 0
        self.bb = 0
        self.sb = 0
        self.button = 0
        self.next2act = 0
        self.aborted = False
        self.nosb = False
        self.butflag = False
        self.bbacted = False
        self.curbet = 0
        self.minraise = 0
        self.pot = 0
        self.pots = []
        self.lastbettor = 0
        self.round = 0
        self.board = []
        self.activelist = []

        #FIXME: Start loading players from the waiting list here...

    def nlive(self):
        'Count how many unbusted players are at the table.'
      
        log.logger.debug('Tourney.nlive()')

        n = 0
        for p in self.players:
            if not p.busted:
                n += 1
        return n

    def newhand(self):
        '''Prepare the table for the next hand.

        As far as the blinds and button go, what happens depends on
        how many players are left and wether or not one or more of the
        blinds were eliminated last hand.  When there are three or
        more players remaining, there are three possible situations:

        - The big blind was eliminated--there will be no small blind
          this hand.  *Next* hand the button goes to the empty seat of
          the player who would have been in the small blind and the
          blinds advance normally.
        
        - The small blind was eliminated--the button goes to the empty
          seat of the player who had the small blind and the blinds
          advance normally.

        - Both blinds survived last hand--button and blinds advance
          normally.

        When there are only two players remaining, the buttons and
        blinds are handled as follows:

        - The big blind advances normally and the other player posts
          the small blind.  The button goes to the small blind.  The
          small blind acts first preflop.  The big blind acts first
          following the flop.
        '''

        log.logger.debug('Tourney.newhand()')

        if self.nlive() == self.nonvacation():
            self.pubout("Everyone's on vacation.   Aborting tourney")
            self.endtourney(True)
        elif self.aborted:
            self.endtourney(True)
        else:
            self.handnum += 1

            # Time to double blinds?
            if self.handsinterval > 0:
                handstogo = self.handnum % self.handsinterval
                if handstogo  ==  0:
                    self.loblind *= 2
                    self.hiblind = self.loblind * 2
                    blindmsg = 'Blinds will double in %d hands.' %\
                                self.handsinterval
                else:
                    if self.handnum > 1:
                        blindmsg = 'Blinds will double '
                        if handstogo > 1:
                            blindmsg += 'in %d hands.' % (handstogo,)
                        else:
                            blindmsg += ' next hand.'
                                  
                    else:
                        blindmsg = 'Blinds will double in %d hands.' %\
                                   (self.handsinterval,)

            else:
                self.dt = datetime(2000, 1, 1)
                self.dt = self.dt.now()
                timexp = (self.dt - self.timestamp).seconds
                if timexp >= self.blindinterval:
                    self.loblind *= 2
                    self.hiblind = self.loblind * 2
                    self.timestamp = self.dt.now()
                    blindmsg = 'Blinds will double in %d seconds.' %\
                               self.blindinterval
                else:
                    blindmsg = 'Blinds will double in %d seconds.' % (self.blindinterval - timexp)

            self.pubout(' ')
            self.pubout('The blinds are currently $%d and $%d.' %\
                        (self.loblind, self.hiblind))

            self.pubout(blindmsg)
            self.pubout(' ')
            
            self.bbacted = False

            if hasattr(self, 'sidepots'):
                delattr(self, 'sidepots')

            for player in self.players:
                player.cmd = Command()
                player.allin = 0
                player.inplay = 0
                player.action = 0
                player.lastbet = 0
                player.folded = False
                player.allin = False
                player.hand.muck()
                if player.vacation:
                    player.cmd.cmd = 'FOLD'

            self.board = []
            self.pot = 0

            self.pubout('Game #%d, %d players.  Dealing Holdem high' %\
                        (self.handnum, self.nlive()))

            if self.nactive() >= 3:

                # If the big blind was eliminated then there's no small
                # blind this hand. Set flag so the button doesn't move
                # next hand.
                if self.players[self.bb].busted:
                    self.nosb = True
                    self.butflag = True
                else:
                    self.nosb = False

                # Who's in the small blind?
                buttonadv = True
                if self.nosb:
                    pass
                else:

                    # The small blind is last hand's big blind
                    self.sb = self.bb

                    # If the small blind was eliminated then the button
                    # stays put
                    if self.players[self.sb].busted:
                        buttonadv = False

                # Who's in the big blind?
                self.bb = self.nextactiveseat(self.bb)

                # Button, button, who gets the button?

                # Do not advance button if this is the second hand
                # following the elimination of the big blind.
                if self.butflag:
                    self.butflag = False
                    buttonadv = False

                if buttonadv:
                    self.button = self.nextactiveseat(self.button)

                else:

                    # If the player with the button is eliminated and
                    # we're not moving the button, then the button moves
                    # *backward* one seat
                    if self.players[self.button].busted:
                        self.button = self.prevactiveseat(self.button)

            else:

                # Heads-up
                self.bb = self.nextactiveseat(self.bb)
                self.sb = self.nextactiveseat(self.sb)
                self.button = self.sb

            self.next2act = self.nextactiveseat(self.bb)

            #self.postantes()

            self.handstatus()
            self.postblinds()

            self.curbet = self.hiblind
            self.lastbettor = self.bb
            self.round = 0

            self.deck.shuffle2(0)
            self.deal()

            for p in self.players:
                if not p.busted:
                    self.noteout(p.nick, 'Your hole cards are: %s' %\
                                 p.hand.showhole())


            self.run()
            #####log.logger.debug('Tourney.newhand:%s is next to act. (%d to call)' %\
            #####                 (self.players[self.next2act].nick,
            #####                  self.curbet - self.players[self.next2act].action))
            #####
            #####self.pubout('%s is next to act. (%d to call)' %\
            #####            (self.players[self.next2act].nick,
            #####            self.curbet - self.players[self.next2act].action))

    def handstatus(self):
        log.logger.debug('Tourney.handstatus()')

        nout = 0
        dealvac = '  '
        msg = ''
        for p in self.players:
            if p.busted:
                continue
            nout += 1
            if p.vacation:
                if self.button == self.players.index(p):
                    dealvac = 'VB'
                else:
                    dealvac = 'V '
            elif self.button == self.players.index(p):
                dealvac = 'B-'

            msg += '%2s%-9s%7d   ' % (dealvac, p.nick, p.bankroll)
            if nout == 3:
                self.pubout(msg)
                dealvac = '  '
                msg = ''
                nout = 0
            else:
                dealvac = '  '

        msg = msg.rstrip()
        if msg:
            self.pubout(msg)

    def postblinds(self):
        'Post blinds.  Handle all-ins.'

        log.logger.debug('Tourney.postblinds()')

        sbbr = self.players[self.sb].bankroll
        if sbbr <= self.loblind:
            self.players[self.sb].bankroll = 0
            self.players[self.sb].inplay = sbbr
            self.players[self.sb].action = sbbr
            self.players[self.sb].allin = True
            self.pot += sbbr
            self.pubout('%s blinds $%d and is all-in.  Pot is now $%d.' %\
                        (self.players[self.sb].nick, sbbr, self.pot))
            log.logger.info('%s blinds $%d and is all-in' %\
                            (self.players[self.sb].nick, sbbr))
            self.sidepots = True
        else:
            self.players[self.sb].bankroll -= self.loblind
            self.players[self.sb].inplay = self.loblind
            self.players[self.sb].action = self.loblind
            self.pot += self.loblind
            self.pubout('%s blinds $%d.  Pot is now $%d.' %\
                        (self.players[self.sb].nick, self.loblind, self.pot))
            log.logger.info('%s blinds $%d' %\
                            (self.players[self.sb].nick,
                             self.loblind))

        bbbr = self.players[self.bb].bankroll
        if bbbr <= self.hiblind:
            self.players[self.bb].bankroll = 0
            self.players[self.bb].inplay = bbbr
            self.players[self.bb].action = bbbr
            self.players[self.bb].allin = True
            self.pot += bbbr
            self.pubout('%s blinds $%d and is all-in.  Pot is now $%d.' %\
                        (self.players[self.bb].nick, bbbr, self.pot))
            log.logger.info('%s blinds $%d and is all-in' %\
                            (self.players[self.bb].nick, bbbr))
            self.sidepots = True
        else:
            self.players[self.bb].bankroll -= self.hiblind
            self.players[self.bb].inplay = self.hiblind
            self.players[self.bb].action = self.hiblind
            self.pot += self.hiblind
            self.pubout('%s blinds $%d.  Pot is now $%d.' %\
                        (self.players[self.bb].nick, self.hiblind, self.pot))
            log.logger.info('%s blinds $%d' %\
                            (self.players[self.bb].nick,
                             self.hiblind))

        self.minraise = self.hiblind

    def nonvacation(self):
        'Count how many players are on vacation'

        log.logger.debug('Tourney.nonvacation()')

        n = 0
        for p in self.players:
            if p.vacation:
                n += 1
        return n

    def nactive(self):
        'Count how many active players are at the table.'

        log.logger.debug('Tourney.nactive()')

        n = 0
        for p in self.players:
            if p.active():
                n += 1
        return n

    def nallin(self):
        'Count how many players are all-in.'

        log.logger.debug('Tourney.nallin()')

        n = 0
        for p in self.players:
            if p.allin:
                n += 1
        return n

    def nquitters(self):
        'Count how many players are quitting.'

        nquitters = 0
        for p in self.players:
            if p.quit:
                nquitters += 1

        return nquitters

    def nextround(self):
        log.logger.debug('Tourney.nextround()')

        # End the hand if we're at the river
        if self.round == Tourney.RIVER:
            self.endhand()
            if not self.playing:
                return
            self.newhand()
            return

        nactive = self.nactive()
        nallin = self.nallin()

        buf = ''
        buf += '%d players' % nactive
        if nallin:
            buf += ', %d all in' % nallin

        log.logger.info(buf)

        # Flip the rest of the board and end the hand
        # if everyone (or nearly everyone) is all in
        if self.nactive() - self.nallin() <= 1:
            self.flipout()
            self.endhand()
            if not self.playing:
                return
            self.newhand()
            return

        # If we get this far, reset current round action
        for p in self.players:
            p.action = 0
            p.lastbet = 0

        self.flipcards()
        self.minraise = self.hiblind
        self.curbet = 0

        # Find the first player to the left of the button who's not all in
        goodbettor = False
        self.lastbettor = self.button
        while not goodbettor:
            self.lastbettor = self.nextactiveseat(self.lastbettor)
            if self.players[self.lastbettor].allin:
                continue
            else:
                goodbettor = True
        
        self.next2act = self.lastbettor


        self.run()
        #####log.logger.debug('Tourney.nextround:%s is next to act. (%d to call)' %\
        #####                 (self.players[self.next2act].nick,
        #####                  self.curbet - self.players[self.next2act].action))
        #####
        #####self.pubout('%s is next to act. (%d to call)' %\
        #####            (self.players[self.next2act].nick,
        #####            self.curbet - self.players[self.next2act].action))

    def flipcards(self):
        log.logger.debug('Tourney.flipcards()')

        buf = ''
        if self.round == Tourney.PREFLOP:
            buf += 'Flop : '
            for i in xrange(3):
                buf += self.board[i].face() + ' '
        elif self.round == Tourney.FLOP:
            buf += 'Turn : '
            buf += self.board[3].face() + ' '    
        elif self.round == Tourney.TURN:
            buf += 'River: '
            buf += self.board[4].face() + ' '    
        self.round += 1

        self.pubout('Board:      %s' % self.printboard(self.round))
        log.logger.info('%s' % buf)

    def flipout(self):
        log.logger.debug('Tourney.flipout()')
        
        while self.round < Tourney.RIVER:
            self.flipcards()

    def begin(self):
        log.logger.debug('Tourney.begin()')
        
        from random import shuffle

        for p in  self.players:
            log.logger.debug('Tourney.begin:%s' % p.nick)

        shuffle(self.players)

        for p in self.players:
            log.logger.debug('Tourney.begin:%s' % p.nick)
            p.bankroll = self.bankroll
        
        self.nstartplayers = len(self.players)
        self.button = len(self.players) - 1
        self.sb = 0
        self.bb = 1

        self.handnum = 0
        self.timestamp = self.dt.now()
        self.newhand()

    def makepots(self):
        log.logger.debug('Tourney.makepots()')

        #FIXME: can we rely on gc here? del?
        self.pots = []

        if hasattr(self, 'sidepots'):
            action = []
            for seat in xrange(len(self.players)):
                action.append(self.players[seat].inplay)

            active = self.activeplayers()
            active.sort(Player.actionsort)

            while len(active):
                p = active.pop(0)
                seat = p.hand.seat
                if action[seat]:

                    # get trigger amount
                    amt = action[seat]

                    # add a new pot, setting the trigger
                    self.pots.append(Pot(amt))

                    # add current player to pot
                    self.pots[-1].players.append(p)

                    # add trigger amount to pot
                    self.pots[-1].value += amt

                    # subtract trigger amount from trigger's action
                    action[seat] -= amt

                    # subtract trigger amount from other active action
                    for o in active:
                        seat = o.hand.seat
                        self.pots[-1].players.append(o)
                        self.pots[-1].value += amt
                        action[seat] -= amt

            # Add leftovers to the first pot
            for amt in action:
                self.pots[0].value += amt

            self.pots.reverse()

        else:
            self.pots.append(Pot())
            self.pots[0].value = self.pot
            self.pots[0].players = self.activeplayers()

        #DEBUG
        #print '%d pots generated' % len(self.pots)
        #for pot in self.pots:
        #    print 'pot %d: trigger: $%d\n value: $%d' %\
        #          (self.pots.index(pot) + 1, pot.trigger, pot.value)
        #    for p in pot.players:
        #        print '\t%s' % p.nick
        #DEBUG
            
    def deal(self):
        log.logger.debug('Tourney.deal()')

        for n in xrange(Tourney.nholecards):
            for p in xrange(len(self.players)):
                player = self.players[(self.button +1+p) % len(self.players)]
                if not player.busted:
                    acard = self.deck.nextcard()
                    player.hand.addcard(acard)
                    player.hand.seat = self.players.index(player)
        for n in xrange(Tourney.nboardcards):
            self.board.append(self.deck.nextcard())
            
    def winseatsort(self, plist):
        '''Sort the winners of a multiway pot clockwise from the dealer.'''

        log.logger.debug('Tourney.winseatsort()')

        sorted = []
        
        for i in xrange(len(self.players)):
            seat = (self.button + i + 1) % len(self.players)
            for p in plist:
                if p.myid == self.players[seat].myid:
                    sorted.append(p)
                    plist.remove(p)
                    break

        return sorted

    #FIXME:  This probably needs modified for Player.quit
    def prevactiveseat(self, seat=-1):
        '''Return the seat number of the player to the right of
        the specified player.
        '''

        log.logger.debug('Tourney.prevactiveseat()')

        if seat >= 0:
            oldas = seat
        else:
            oldas = self.next2act

        if oldas == 0:
            newas = len(self.players) - 1
        else:
            newas = oldas - 1

        while newas != oldas:
            if(not self.players[newas].folded and
               not self.players[newas].busted):
                return newas
            if newas == 0:
                newas = len(self.players) - 1
            else:
                newas -= 1
        return oldas

    def dohelp(self, pid):

        self.noteout(pid, 'Dealer commands:')
        self.noteout(pid, '----------------')
        self.noteout(pid, ' ')
        self.noteout(pid, "join <password> - Attempt to join the next tournament.")
        self.noteout(pid, "quit - Quit immediately.  Any money you've put into the pot stays there.")
        self.noteout(pid, "password <newpassword> - replace your password with newpassword.  You must be successfully joined to use this command.")
        self.noteout(pid, ' ')
        self.noteout(pid, "blind <amount> - Set the size of the small blind.")
        self.noteout(pid, "double <interval> [hands] - Set time interval (seconds) for doubling the blinds.  Optional 'hands' argument changes interval to the number of hands.")
        self.noteout(pid, "bankroll <amount> - Set the size of the initial bankroll for all players.")
        self.noteout(pid, "start - Start the tournament.  There must be 2-23 players joined.")
        self.noteout(pid, "abort - Abort the tournament.  Players will remain joined.")
        self.noteout(pid, ' ')
        self.noteout(pid, "check - Get a warning if there's a bet to you.")
        self.noteout(pid, "fold - Fold at your earliest opportunity.")
        self.noteout(pid, "jam - Go all in.")
        self.noteout(pid, "pot - Call and raise the value of the pot.")
        self.noteout(pid, "call [amount] - Call any bet if you don't specify amount.")
        self.noteout(pid, "make <amount> - Make the bet <amount>.  Will call or raise depending on amount.")
        self.noteout(pid, "raise <amount> - Attempt to raise <amount>.")
        self.noteout(pid, "undo - Undo any advance action.")        
        self.noteout(pid, ' ')
        self.noteout(pid, "vacation [nick] - Without an argument, send yourself on vacation.  Otherwise, send nick on vacation.")
        self.noteout(pid, "back - come back from vacation.  You can only bring yourself back.")
        self.noteout(pid, "remind <nick> - Remind nick that it's their turn to act.")
        self.noteout(pid, ' ')
        self.noteout(pid, "cards - Look at your hole cards.")
        self.noteout(pid, "board - Look at the board.")
        self.noteout(pid, "status - Print WRGPT-style status message.")
        self.noteout(pid, ' ')
        self.noteout(pid, "commands - List of dealer commands (*this* list!)")

