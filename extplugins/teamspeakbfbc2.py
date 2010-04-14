# -*- coding: utf-8 -*-
#
# PowerAdmin Plugin for BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2008 Mark Weirath (xlr8or@xlr8or.com)
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#
# CHANGELOG :
# 2010/04/13 - 1.0 - Courgette
# * first version
#
#
#

__version__ = '1.0'
__author__  = 'Courgette'

import time, string
import b3
import b3.events
import b3.plugin
import string

#--------------------------------------------------------------------------------------------------
class Teamspeakbfbc2Plugin(b3.plugin.Plugin):

    connected = False

    _adminPlugin = None
    
    TS3ServerIP = None
    TS3QueryPort = 10011
    TS3ServerID = None
    TS3Login = None
    TS3Password = None
    TS3ChannelB3 = 'B3 autoswitched channels'
    TS3ChannelTeam1 = 'Team A'
    TS3ChannelTeam2 = 'Team B'
    
    
    tsconnection = None
    tsServerPort = 'unknown'
    
    tsChannelIdB3 = None
    tsChannelIdTeam1 = None
    tsChannelIdTeam2 = None
    
    squadNames = {
        1: 'Alpha',
        2: 'Bravo',
        3: 'Charlie',
        4: 'Delta',
        5: 'Echo',
        6: 'Foxtrot',
        7: 'Golf',
        8: 'Hotel',
    }
    
    tsChannelIdSquadsTeam1 = {
        1: None,
        2: None,
        3: None,
        4: None,
        5: None,
        6: None,
        7: None,
        8: None,
    }
    tsChannelIdSquadsTeam2 = {
        1: None,
        2: None,
        3: None,
        4: None,
        5: None,
        6: None,
        7: None,
        8: None,
    }

    def startup(self):
        """\
        Initialize plugin settings
        """
        
        if self.console.gameName != 'bfbc2':
            raise SystemExit('The Teamspeakbfbc2 plugin require the BFBC2 parser to run')

        # get the admin plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False
    
        # register our commands
        if 'commands' in self.config.sections():
            for cmd in self.config.options('commands'):
                level = self.config.get('commands', cmd)
                sp = cmd.split('-')
                alias = None
                if len(sp) == 2:
                    cmd, alias = sp
            
                func = self.getCmd(cmd)
                if func:
                    self._adminPlugin.registerCommand(self, cmd, level, func, alias)

        # Register our events
        self.verbose('Registering events')
        #self.registerEvent(b3.events.EVT_CLIENT_TEAM_CHANGE)
        self.registerEvent(b3.events.EVT_CLIENT_SQUAD_CHANGE)
    
        self.debug('Started')


    def getCmd(self, cmd):
        cmd = 'cmd_%s' % cmd
        if hasattr(self, cmd):
            func = getattr(self, cmd)
            return func
    
        return None


    def onLoadConfig(self):
        self.connected = False
        self.readConfig()
        
        try:
            self.connectToTS()
            self.connected = True
            self.createChannels()
        except TS3Error, err:
            self.error(err)
    
    def readConfig(self):
        try:
            self.TS3ServerIP = self.config.get('teamspeakServer', 'host')
        except:
            self.error('Cannot get teamspeak server host from config file')
            raise SystemExit('invalid teamspeak configuration')
      
        try:
            self.TS3QueryPort = self.config.getint('teamspeakServer', 'queryport')
        except:
            self.error('Cannot get teamspeak server queryport from config file, using default : %s' % self.TS3QueryPort)
      
        try:
            self.TS3ServerID = self.config.getint('teamspeakServer', 'id')
        except:
            self.error('Cannot get teamspeak server Id from config file')
            raise SystemExit('invalid teamspeak configuration')

        try:
            self.TS3Login = self.config.get('teamspeakServer', 'login')
        except:
            self.error('Cannot get teamspeak login from config file')
            raise SystemExit('invalid teamspeak configuration')
      
        try:
            self.TS3Password = self.config.get('teamspeakServer', 'password')
        except:
            self.error('Cannot get teamspeak password from config file')
            raise SystemExit('invalid teamspeak configuration')
      
        
        try:
            self.TS3ChannelB3 = self.config.get('teamspeakChannels', 'B3')
            self.info('teamspeakChannels::B3 : \'%s\'' % self.TS3ChannelB3)
        except:
            self.info('Cannot get teamspeakChannels::B3 from config file, using default : %s' % self.TS3ChannelB3)
      
        try:
            self.TS3ChannelTeam1 = self.config.get('teamspeakChannels', 'team1')
            self.info('teamspeakChannels::team1 : \'%s\'' % self.TS3ChannelTeam1)
        except:
            self.info('Cannot get teamspeakChannels::team1 from config file, using default : %s' % self.TS3ChannelTeam1)
      
        try:
            self.TS3ChannelTeam2 = self.config.get('teamspeakChannels', 'team2')
            self.info('teamspeakChannels::team2 : \'%s\'' % self.TS3ChannelTeam2)
        except:
            self.info('Cannot get teamspeakChannels::team2 from config file, using default : %s' % self.TS3ChannelTeam2)
      
      

    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if event.type == b3.events.EVT_STOP:
            self.deleteChannels()
            self.tsconnection.disconnect()
            
        if self.connected == False:
            return
#        if event.type == b3.events.EVT_CLIENT_TEAM_CHANGE:
#            if event.data == b3.TEAM_BLUE:
#                self.moveClientToTeam1(event.client)
#            elif event.data == b3.TEAM_RED:
#                self.moveClientToTeam2(event.client)
#            else:
#                self.moveClientToB3Channel(event.client)
#
        if event.type == b3.events.EVT_CLIENT_SQUAD_CHANGE:
            client = event.client
            if client:
                try:
                    tsclient = self.tsGetClient(client)
                    if tsclient:
                        if client.team == b3.TEAM_BLUE:
                            if int(client.squad) >= 1 and int(client.squad) <=8:
                                self.moveClientToTeam1Squad(client, client.squad)
                            else:
                                self.moveClientToTeam1(client)
                        elif client.team == b3.TEAM_RED:
                            if int(client.squad) >= 1 and int(client.squad) <=8:
                                self.moveClientToTeam2Squad(client, client.squad)
                            else:
                                self.moveClientToTeam2(client)
                        else:
                            self.moveClientToB3Channel(event.client)
                except TS3Error, err:
                    self.error(err)



    def cmd_tsreconnect(self ,data , client, cmd=None):
        """\
        Reconnect B3 to the Teamspeak server
        """
        if client:
            client.message('Reconnecting to TS on %s:%s ...' % (self.TS3ServerIP, self.TS3QueryPort))
            try:
                self.connectToTS()
                self.createChannel()
            except TS3Error, err:
                client.message('Failed to connect : %s' % err.msg)
                self.error(err)


    def cmd_tsdisconnect(self ,data , client, cmd=None):
        """\
        Disconnect B3 from the Teamspeak server
        """
        if client:
            client.message('Disconnecting from TS on %s:%s ...' % (self.TS3ServerIP, self.TS3QueryPort))
            try:
                self.tsconnection.disconnect()
                self.connected = False
            except TS3Error, err:
                client.message('Failed to disconnect : %s' % err.msg)
                self.error(err)


    def cmd_teamspeak(self ,data , client, cmd=None):
        """\
        Teamspeak server info
        """
        if client:
            if self.connected:
                tsclient = self.tsGetClient(client)
                if tsclient is None:
                    client.message('Teamspeak server on %s:%s' % (self.TS3ServerIP, self.tsServerPort))
                else:
                    client.message('You are connected on Teamspeak')
                    client.message('You will be automatically switched to your team/squad channel')
            else:
                client.message('Teamspeak server not available')
                
                
    def cmd_tslist(self ,data ,client, cmd=None):
        """Return a list of all people on ts
        """
        if not client:
            return None
        clientlist = self.tsconnection.command('clientlist')
        self.debug('clientlist: %s' % clientlist)
        for c in clientlist:
            nick = c['client_nickname']
            client.message('Teamspeak Client %s : %s' % (c, nick))
        return None

        
    def cmd_tskick(self ,data ,client, cmd=None):
        """<name> Kick a user from TeamSpeak
        """
        if not client:
            return None
        message = 'Kicked-by-admin'
        clientlist = self.tsconnection.command('clientlist')
        for c in clientlist:
            nick = c['client_nickname']
            if nick in (data):
                data = self.tsconnection.command('clientkick', {'clid': c['clid']}, 'reasonid':'4', 'reasonmsg':'%s' % message)
                self.debug('client data : %s' % data)
                client.message('Teamspeak Client %s was kicked' % nick)
                return data
            #clientkick clid=5|clid=6 reasonid=4 reasonmsg=Go\saway!
        return None        
        

    def moveClientToB3Channel(self, client):
        self.tsMoveClientToChannelId(client, self.tsChannelIdB3)

    def moveClientToTeam1(self, client):
        self.tsMoveClientToChannelId(client, self.tsChannelIdTeam1)
                
    def moveClientToTeam2(self, client):
        self.tsMoveClientToChannelId(client, self.tsChannelIdTeam2)
    
    def moveClientToTeam1Squad(self, client, squad):
        cid = self.tsChannelIdSquadsTeam1[int(squad)]
        self.tsMoveClientToChannelId(client, cid)

    def moveClientToTeam2Squad(self, client, squad):
        cid = self.tsChannelIdSquadsTeam2[int(squad)]
        self.tsMoveClientToChannelId(client, cid)

    def connectToTS(self):
        if self.tsconnection is not None:
            try:
                self.tsconnection.disconnect()
            except:
                pass
            del self.tsconnection
            
        self.tsconnection = ServerQuery(self.TS3ServerIP, self.TS3QueryPort)
        
        self.info('connecting to teamspeak server %s:%s' % (self.TS3ServerIP, self.TS3QueryPort))
        self.tsconnection.connect()
        
        self.info('TS version : %s' % self.tsconnection.command('version'))
        
        self.info('Loging to TS server with login name \'%s\'' % self.TS3Login)
        self.tsconnection.command('login', {'client_login_name': self.TS3Login, 'client_login_password': self.TS3Password})
        
        self.info('Joining server ID : %s' % self.TS3ServerID)
        self.tsconnection.command('use', {'sid': self.TS3ServerID})
        
        self.info('Get server port')
        serverinfo = self.tsconnection.command('serverinfo')
        self.tsServerPort = serverinfo['virtualserver_port']
        self.info('TS server port is %s', self.tsServerPort)
    
    
    def createChannels(self):
        channellist = self.tsconnection.command('channellist')
        self.debug('channellist : %s' % channellist)
        
        
        self.tsChannelIdB3 = self.tsGetChannelIdByName(self.TS3ChannelB3, channellist)
        if self.tsChannelIdB3 is None:
            self.info('creating channel [%s]' % self.TS3ChannelB3)
            response = self.tsconnection.command('channelcreate', 
                                                              {'channel_name': self.TS3ChannelB3
                                                               ,'channel_flag_semi_permanent': 1})
            self.debug(response)
            self.tsChannelIdB3 = response['cid']
            
            
        self.tsChannelIdTeam1 = self.tsGetChannelIdByName(self.TS3ChannelTeam1, channellist, self.tsChannelIdB3)
        if self.tsChannelIdTeam1 is None:
            self.info('creating sub-channel [%s]' % self.TS3ChannelTeam1)
            response = self.tsconnection.command('channelcreate', 
                                                              {'channel_name': self.TS3ChannelTeam1, 
                                                               'cpid': self.tsChannelIdB3
                                                               ,'channel_flag_semi_permanent': 1})
            self.debug(response)
            self.tsChannelIdTeam1 = response['cid']
        
        
        self.tsChannelIdTeam2 = self.tsGetChannelIdByName(self.TS3ChannelTeam2, channellist, self.tsChannelIdB3)
        if self.tsChannelIdTeam2 is None:
            self.info('creating sub-channel [%s]' % self.TS3ChannelTeam2)
            response = self.tsconnection.command('channelcreate', 
                                                              {'channel_name': self.TS3ChannelTeam2, 
                                                               'cpid': self.tsChannelIdB3
                                                               ,'channel_flag_semi_permanent': 1})
            self.debug(response)
            self.tsChannelIdTeam2 = response['cid']

        
        for i in range(1,9):
            self.tsChannelIdSquadsTeam1[i] = self.tsGetChannelIdByName(self.squadNames[i], channellist, self.tsChannelIdTeam1)
            if self.tsChannelIdSquadsTeam1[i] is None:
                self.info('creating squad-channel [%s] for team1' % self.squadNames[i])
                self.tsChannelIdSquadsTeam1[i] = self.tsCreateSubChannel(self.squadNames[i], self.tsChannelIdTeam1)
        
            self.tsChannelIdSquadsTeam2[i] = self.tsGetChannelIdByName(self.squadNames[i], channellist, self.tsChannelIdTeam2)
            if self.tsChannelIdSquadsTeam2[i] is None:
                self.info('creating squad-channel [%s] for team2' % self.squadNames[i])
                self.tsChannelIdSquadsTeam2[i] = self.tsCreateSubChannel(self.squadNames[i], self.tsChannelIdTeam2)
            
    def deleteChannels(self):
        if self.connected:
            self.tsconnection.command('channeldelete', {'cid': self.tsChannelIdB3})
        
    def tsCreateSubChannel(self, channelName, parentChannelId):
        response = self.tsconnection.command('channelcreate', 
                                  {'channel_name': channelName, 
                                   'cpid': parentChannelId
                                   ,'channel_flag_semi_permanent': 1})
        return response['cid']

            
    def tsGetChannelIdByName(self, channelName, channellist=[], parentChannel=None):
        cid = None
        for c in channellist:
            if c['channel_name'] == channelName and (parentChannel is None or c['pid'] == parentChannel):
                cid = c['cid']
        return cid

    
    def tsGetClient(self, client):
        """Return a dict with all TS client properties as returned by the 
        clientinfo command
        """
        if not client:
            return None
        clientlist = self.tsconnection.command('clientlist')
        self.debug('clientlist: %s' % clientlist)
        for c in clientlist:
            nick = c['client_nickname'].lower()
            if nick in (client.name.lower(), client.cid.lower()):
                data = self.tsconnection.command('clientinfo', {'clid': c['clid']})
                self.debug('client data : %s' % data)
                data['clid'] = c['clid']
                return data
        return None
    
        
    def tsMoveClientToChannelId(self, client, tsChannelId):
        if client and self.connected:
            tsclient = self.tsGetClient(client)
            if tsclient:
                self.info('moving %s (clid:%s) to channel ID %s' % (client.cid, tsclient['clid'], tsChannelId))
                self.tsconnection.command('clientmove', {'clid': tsclient['clid'], 'cid': tsChannelId})
 
    
    
    
##################################################################################################
# Copyright (c) 2009 Christoph Heer (Christoph.Heer@googlemail.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the \"Software\"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import telnetlib
import re
import thread
import time


class TS3Error(Exception):

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __str__(self):
        return "ID %s (%s)" % (self.code, self.msg)


class ServerQuery():
    TSRegex = re.compile(r"(\w+)=(.*?)(\s|$|\|)")

    def __init__(self, ip='127.0.0.1', query=10011):
        """
        This class contains functions to connecting a TS3 Query Port and send
        command.
        @param ip: IP adress of the TS3 Server
        @type ip: str
        @param query: Query Port of the TS3 Server. Default 10011
        @type query: int
        """
        self.IP = ip
        self.Query = int(query)
        self.Timeout = 5.0

    def connect(self):
        """
        Open a link to the Teamspeak 3 query port
        @return: A tulpe with a error code. Example: ('error', 0, 'ok')
        """
        try:
            self.telnet = telnetlib.Telnet(self.IP, self.Query)
        except telnetlib.socket.error:
            raise TS3Error(10, 'Can not open a link on the port or IP')
        output = self.telnet.read_until('TS3', self.Timeout)
        if output.endswith('TS3') == False:
            raise TS3Error(20, 'This is not a Teamspeak 3 Server')
        else:
            return True

    def disconnect(self):
        """
        Close the link to the Teamspeak 3 query port
        @return: ('error', 0, 'ok')
        """
        self.telnet.write('quit \n')
        self.telnet.close()
        return True

    def escaping2string(self, string):
        """
        Convert the escaping string form the TS3 Query to a human string.
        @param string: A string form the TS3 Query with ecaping.
        @type string: str
        @return: A human string with out escaping.
        """
        string = str(string)
        string = string.replace('\/', '/')
        string = string.replace('\s', ' ')
        string = string.replace('\p', '|')
        string = string.replace('\n', '')
        string = string.replace('\r', '')
        try:
            string = int(string)
            return string
        except ValueError:
            ustring = unicode(string, "utf-8")
            return ustring

    def string2escaping(self, string):
        """
        Convert a human string to a TS3 Query Escaping String.
        @param string: A normal/human string.
        @type string: str
        @return: A string with escaping of TS3 Query.
        """
        if type(string) == type(int()):
            string = str(string)
        else:
            string = string.encode("utf-8")
            string = string.replace('/', '\\/')
            string = string.replace(' ', '\\s')
            string = string.replace('|', '\\p')
        return string

    def command(self, cmd, parameter={}, option=[]):
        """
        Send a command with paramters and options to the TS3 Query.
        @param cmd: The command who wants to send.
        @type cmd: str
        @param parameter: A dict with paramters and value.
        Example: sid=2 --> {'sid':'2'}
        @type cmd: dict
        @param option: A list with options. Example: �uid --> ['uid']
        @type option: list
        @return: The answer of the server as tulpe with error code and message.
        """
        telnetCMD = cmd
        for key in parameter:
            telnetCMD += " %s=%s" % (key, self.string2escaping(parameter[key]))
        for i in option:
            telnetCMD += " -%s" % (i)
        telnetCMD += '\n'
        self.telnet.write(telnetCMD)

        telnetResponse = self.telnet.read_until("msg=ok", self.Timeout)
        telnetResponse = telnetResponse.split(r'error id=')
        notParsedCMDStatus = "id=" + telnetResponse[1]
        notParsedInfo = telnetResponse[0].split('|')

        if (cmd.endswith("list") == True) or (len(notParsedInfo) > 1):
            returnInfo = []
            for notParsedInfoLine in notParsedInfo:
                ParsedInfo = self.TSRegex.findall(notParsedInfoLine)
                ParsedInfoDict = {}
                for ParsedInfoKey in ParsedInfo:
                    ParsedInfoDict[ParsedInfoKey[0]] = self.escaping2string(
                        ParsedInfoKey[1])
                returnInfo.append(ParsedInfoDict)

        else:
            returnInfo = {}
            ParsedInfo = self.TSRegex.findall(notParsedInfo[0])
            for ParsedInfoKey in ParsedInfo:
                returnInfo[ParsedInfoKey[0]] = self.escaping2string(
                    ParsedInfoKey[1])

        ReturnCMDStatus = {}
        ParsedCMDStatus = self.TSRegex.findall(notParsedCMDStatus)
        for ParsedCMDStatusLine in ParsedCMDStatus:
            ReturnCMDStatus[ParsedCMDStatusLine[0]] = self.escaping2string(
                ParsedCMDStatusLine[1])
        if ReturnCMDStatus['id'] != 0:
            raise TS3Error(ReturnCMDStatus['id'], ReturnCMDStatus['msg'])

        return returnInfo


class ServerNotification(ServerQuery):
    def __init__(self, ip='127.0.0.1', query=10011):
        """
        This class contains functions to work with the
        ServerNotification of TS3.
        @param ip: IP adress of the TS3 Server
        @type ip: str
        @param query: Query Port of the TS3 Server. Default 10011
        @type query: int
        """
        self.IP = ip
        self.Query = int(query)
        self.Timeout = 5.0
        self.LastCommand = 0

        self.Lock = thread.allocate_lock()
        self.RegistedNotifys = []
        self.RegistedEvents = []
        thread.start_new_thread(self.worker, ())

    def worker(self):
        while True:
            self.Lock.acquire()
            RegistedNotifys = self.RegistedNotifys
            LastCommand = self.LastCommand
            self.Lock.release()
            if len(RegistedNotifys) == 0:
                continue
            if LastCommand < time.time() - 180:
                self.command('version')
                self.Lock.acquire()
                self.LastCommand = time.time()
                self.Lock.release()
            telnetResponse = self.telnet.read_until("\n", 0.1)
            if telnetResponse.startswith('notify'):
                notifyName = telnetResponse.split(' ')[0]
                ParsedInfo = self.TSRegex.findall(telnetResponse)
                notifyData = {}
                for ParsedInfoKey in ParsedInfo:
                    notifyData[ParsedInfoKey[0]] = self.escaping2string(
                        ParsedInfoKey[1])
                for RegistedNotify in RegistedNotifys:
                    if RegistedNotify['notify'] == notifyName:
                        RegistedNotify['func'](notifyName, notifyData)
            time.sleep(0.2)

    def registerNotify(self, notify, func):
        notify2func = {'notify': notify, 'func': func}

        self.Lock.acquire()
        self.RegistedNotifys.append(notify2func)
        self.LastCommand = time.time()
        self.Lock.release()

    def unregisterNotify(self, notify, func):
        notify2func = {'notify': notify, 'func': func}

        self.Lock.acquire()
        self.RegistedNotifys.remove(notify2func)
        self.LastCommand = time.time()
        self.Lock.release()

    def registerEvent(self, eventName, parameter={}, option=[]):
        parameter['event'] = eventName
        self.RegistedEvents.append(eventName)
        self.command('servernotifyregister', parameter, option)
        self.Lock.acquire()
        self.LastCommand = time.time()
        self.Lock.release()

    def unregisterEvent(self):
        self.command('servernotifyunregister')
        

##################################################################################################


if __name__ == '__main__':
    from b3.fake import fakeConsole
    from b3.fake import joe
    import time
    
    from b3.config import XmlConfigParser
    
    conf = XmlConfigParser()
    conf.setXml("""
    <configuration plugin="teamspeakbfbc2">
        <settings name="teamspeakServer">
            <!-- IP or domain where your teamspeak server is hosted -->
            <set name="host">127.0.0.1</set>
            <!-- query port of your teamspeak server (default: 10011) -->
            <set name="queryport">10011</set>
            <!-- Teamspeak virtual server ID -->
            <set name="id">1</set>
            <!-- B3 login information. You need to create a ServerQuery Login for B3 -->
            <set name="login">B3</set>
            <set name="password">N37Asi5+</set>
        </settings>
        <settings name="teamspeakChannels">
            <set name="B3">B3 channel</set>
            <set name="team1">Team Alpha</set>
            <set name="team2">Team Bravo</set>
        </settings>
        <settings name="commands">
            <!-- set here levels needed to be allowed to use commands.
                You can define a command alias adding '-' and the alias after the command name.
                Levels:
                0 : everyone
                1 : registered users
                2 : regular users
                20 : moderators
                40 : admins
                60 : full admins
                80 : senior admins
                100 : super admins
            -->
            
            <set name="tsreconnect">100</set>
            <set name="teamspeak-ts">1</set>
        </settings>
    </configuration>
    """)

    ## add BFBC2 specific events we'd like to test on this fake console
    fakeConsole.Events.createEvent('EVT_CLIENT_SQUAD_CHANGE', 'Client Squad Change')
    fakeConsole.game = 'bfbc2'
    
    ## create an instance of the plugin to test
    p = Teamspeakbfbc2Plugin(fakeConsole, conf)
    p.onStartup()

    joe.connects('Joe')
    joe.says("!ts")
    time.sleep(2)
    
    joe.cid = 'Courgette'
    joe.says("!ts")
    time.sleep(2)
    
    
    import unittest
    
    class TestTeamspeakbfbc2(unittest.TestCase):
        def test_teamMisc(self):
            joe.team = b3.TEAM_SPEC
            joe.squad = 0
            fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_SQUAD_CHANGE, (joe.team, joe.squad), joe))
            time.sleep(.2)
            tsclient = p.tsGetClient(joe)
            self.assertEqual(tsclient['cid'], p.tsChannelIdB3)

        def test_team1(self):
            joe.team = b3.TEAM_BLUE
            joe.squad = 0
            fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_SQUAD_CHANGE, (joe.team, joe.squad), joe))
            time.sleep(.2)
            tsclient = p.tsGetClient(joe)
            self.assertEqual(tsclient['cid'], p.tsChannelIdTeam1)
        
        def test_team2(self):
            joe.team = b3.TEAM_RED
            joe.squad = 0
            fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_SQUAD_CHANGE, (joe.team, joe.squad), joe))
            time.sleep(.2)
            tsclient = p.tsGetClient(joe)
            self.assertEqual(tsclient['cid'], p.tsChannelIdTeam2)

        def test_squadsTeam1(self):
            joe.team = b3.TEAM_BLUE
            for i in range(1,9):
                joe.squad = i
                fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_SQUAD_CHANGE, (joe.team, joe.squad), joe))
                time.sleep(.2)
                tsclient = p.tsGetClient(joe)
                self.assertEqual(tsclient['cid'], p.tsChannelIdSquadsTeam1[i])

        def test_squadsTeam2(self):
            joe.team = b3.TEAM_RED
            for i in range(1,9):
                joe.squad = i
                fakeConsole.queueEvent(b3.events.Event(b3.events.EVT_CLIENT_SQUAD_CHANGE, (joe.team, joe.squad), joe))
                time.sleep(.2)
                tsclient = p.tsGetClient(joe)
                self.assertEqual(tsclient['cid'], p.tsChannelIdSquadsTeam2[i])
    
    def donothing(*whatever):
        pass
    fakeConsole.error = donothing
    fakeConsole.debug = donothing
    fakeConsole.bot = donothing
    fakeConsole.verbose = donothing
    fakeConsole.verbose2 = donothing
    fakeConsole.console = donothing
    fakeConsole.warning = donothing
    fakeConsole.info = donothing
    fakeConsole.exception = donothing
    fakeConsole.critical = donothing
    
    unittest.main()
