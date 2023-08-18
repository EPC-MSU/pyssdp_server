from lib.ssdp import SSDPServer, logger
import socket
import random
from email.utils import formatdate
import ifaddr
from errno import ENOPROTOOPT
import sys


SSDP_PORT = 1900
SSDP_ADDR = '239.255.255.250'
adapters = ifaddr.get_adapters()
bad_interfaces = []


class UPNPSSDPServer(SSDPServer):
    def __init__(self):
        SSDPServer.__init__(self)

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except socket.error as le:
                # RHEL6 defines SO_REUSEPORT but it doesn't work
                if le.errno == ENOPROTOOPT:
                    pass
                else:
                    raise

        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 32)

        ssdp_addr = socket.inet_aton(SSDP_ADDR)


        from platform import system
        if system() == 'Linux':
            logger.info("Linux system. Will try to join multicast on interface 0.0.0.0")
            interface = socket.inet_aton('0.0.0.0')
            try:
                self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, ssdp_addr + interface)
                logger.info('Joined multicast on interface 0.0.0.0')
            except socket.error as msg:
                logger.warn("Failed to join multicast on interface 0.0.0.0: %r" % msg)
        else:
            logger.info("Not a Linux system. Joining multicast on all interfaces")
            if_count = 0
            for adapter in adapters:
                for ip in adapter.ips:
                    if not isinstance(ip.ip, str):
                        continue
                    if ip.ip == '127.0.0.1':
                        continue

                    if_count += 1
                    interface = socket.inet_aton(ip.ip)
                    try:
                        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, ssdp_addr + interface)
                        logger.info('Joined multicast on interface %s/%d' % (ip.ip, ip.network_prefix))
                    except socket.error as msg:
                        logger.warn("Failed to join multicast on interface %s. This interface will be ignored. %r"
                                    % (ip.ip, msg))
                        bad_interfaces.append(ip.ip)
                        continue
            if if_count == len(bad_interfaces):
                logger.warn("Failed to join multicast on all interfaces. Server won't be able to send NOTIFY messages.")

        try:
            self.sock.bind(('0.0.0.0', SSDP_PORT))
        except (OSError) as e:
            logger.fatal("""Error creating ssdp server on port %d. Please check that the port is not in use: %r"""
                         % (SSDP_PORT, e))
            sys.exit()
        self.sock.settimeout(1)

        # usn = None
        # for i in self.known.values():
        #     for k, v in i.items():
        #         if k == 'USN':
        #             usn = v

        # import time
        # self.do_notify(usn)
        # time.sleep(5)

        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                self.datagram_received(data, addr)
            except socket.timeout:
                continue
        self.shutdown()
        
    def datagram_received(self, data, host_port):
        """Handle a received multicast datagram."""

        (host, port) = host_port

        try:
            header, payload = data.decode().split('\r\n\r\n')[:2]
            #print(data.decode())
        except ValueError as err:
            logger.error(err)
            return

        lines = header.split('\r\n')
        cmd = lines[0].split(' ')
        lines = map(lambda x: x.replace(': ', ':', 1), lines[1:])
        lines = filter(lambda x: len(x) > 0, lines)

        headers = [x.split(':', 1) for x in lines]
        headers = dict(map(lambda x: (x[0].lower(), x[1]), headers))

        logger.info('SSDP command %s %s - from %s:%d' % (cmd[0], cmd[1], host, port))
        logger.debug('with headers: {}.'.format(headers))
        if cmd[0] == 'M-SEARCH' and cmd[1] == '*':
            # SSDP discovery
            self.discovery_request(headers, (host, port))
        elif cmd[0] == 'NOTIFY' and cmd[1] == '*':
            # SSDP presence
            logger.debug('NOTIFY *')
        else:
            logger.warning('Unknown SSDP command %s %s' % (cmd[0], cmd[1]))
    
        
    def send_it(self, response, destination, delay, usn):
        logger.info('HTTP/1.1 200 OK response delayed by %ds to %r' % (delay, destination))
        try:
            self.sock.sendto(response.encode(), destination)
        except (AttributeError, socket.error) as msg:
            logger.warning("failure sending out byebye notification: %r" % msg)
            
    
    def do_notify(self, usn):
        """Do notification"""

        if self.known[usn]['SILENT']:
            return
        logger.info('NOTIFY response for %s' % usn)

        resp = [
            'NOTIFY * HTTP/1.1',
            'HOST: %s:%d' % (SSDP_ADDR, SSDP_PORT),
            'NTS: ssdp:alive',
        ]
        stcpy = dict(self.known[usn].items())
        stcpy['NT'] = stcpy['ST']
        del stcpy['ST']
        del stcpy['MANIFESTATION']
        del stcpy['SILENT']
        del stcpy['HOST']
        del stcpy['last-seen']

        resp.extend(map(lambda x: ': '.join(x), stcpy.items()))
        resp.extend(('', ''))
        logger.debug('do_notify content', resp)
        try:
            self.sock.sendto('\r\n'.join(resp).encode(), (SSDP_ADDR, SSDP_PORT))
            self.sock.sendto('\r\n'.join(resp).encode(), (SSDP_ADDR, SSDP_PORT))
        except (AttributeError, socket.error) as msg:
            logger.warning("failure sending out alive notification: %r" % msg)

    def discovery_request(self, headers, host_port):

        (host, port) = host_port

        logger.debug('Discovery request from (%s,%d) for %s' % (host, port, headers['st']))
        logger.debug('Discovery request for %s' % headers['st'])

        # Do we know about this service?
        for i in self.known.values():
            if i['MANIFESTATION'] == 'remote':
                continue
            if headers['st'] == 'ssdp:all' and i['SILENT']:
                continue
            if i['ST'] == headers['st'] or headers['st'] == 'ssdp:all':
            
                print()
                print()
                logger.info('Discovery request from (%s,%d) for %s' % (host, port, headers['st']))
                
                response = ['HTTP/1.1 200 OK']

                usn = None
                for k, v in i.items():
                    if k == 'USN':
                        usn = v
                    if k == 'LOCATION':
                        v = '/Basic_info.xml'
                    if k not in ('MANIFESTATION', 'SILENT', 'HOST'):
                        response.append('%s: %s' % (k, v))

                if usn:
                    response.append('DATE: %s' % formatdate(timeval=None, localtime=False, usegmt=True))

                    response.extend(('', ''))
                    delay = random.randint(0, int(headers['mx']))

                    self.send_it('\r\n'.join(response), (host, port), delay, usn)

                    # NOTIFY - to make sure the response reaches Revealer

                    for adapter in adapters:
                        for ip in adapter.ips:
                            if not isinstance(ip.ip, str):
                                continue
                            if ip.ip == '127.0.0.1':
                                continue
                            if ip.ip in bad_interfaces:
                                continue

                            if_addr = socket.inet_aton(ip.ip)
                            try:
                                self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, if_addr)
                                logger.info('Set interface to %s' % ip.ip)
                            except socket.error as msg:
                                logger.warn("Failure connecting to interface %s: %r" % (ip.ip, msg))
                                continue

                            # format: LOCATION: http://172.16.130.67:80/Basic_info.xml
                            url = 'http://{}:80/Basic_info.xml'.format(ip.ip)
                            self.known[usn]['LOCATION'] = url

                            self.do_notify(usn)
                            
                    print()
                    print()