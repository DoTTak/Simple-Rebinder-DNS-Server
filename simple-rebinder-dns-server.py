import random
from dnslib import DNSRecord, QTYPE, RR, A, RCODE
from dnslib.server import DNSServer, BaseResolver


class RebindResolver(BaseResolver):
    def __init__(self, rebinder_dns):
        # Dictionary to store session-specific states
        self.sessions = {}
        self.rebinder_dns = rebinder_dns

    def resolve(self, request, handler):

        # Retrieve the requested domain name and query type
        qname = request.q.qname
        qtype = QTYPE[request.q.qtype]
        
        # Generate DNS response
        reply = request.reply()
        
        domain = str(qname).lower()

        # Parse domain format
        if not domain.endswith(f".{self.rebinder_dns}."):
            reply.header.rcode = RCODE.NXDOMAIN
            return reply

        # Remove `rebind-` and parse the domain
        try:
            stripped_domain = domain.replace(f".{self.rebinder_dns}.", "")  # Remove `.self.rebinder_dns.`
            
            parts = stripped_domain.split("-")  # Format: '{src}-{dst}-{session}-{option}'
            if len(parts) != 4:
                raise ValueError("Invalid format")

            src, dst, session, option = parts[0], parts[1], parts[2], parts[3]

        except ValueError:
            reply.header.rcode = RCODE.NXDOMAIN
            return reply

        if qtype != "A":
            reply.header.rcode = RCODE.NXDOMAIN
            return reply

        # Handle options
        if option == "fs":  # First then always second
            if session not in self.sessions:
                # If the session does not exist, store src and return src
                self.sessions[session] = src
                answer_ip = src
            else:
                # If the session exists, always return dst
                self.sessions[session] = dst
                answer_ip = dst

            reply.add_answer(RR(qname, QTYPE.A, rdata=A(answer_ip), ttl=0))
        
        elif option == "ma":  # Multiple answers
            reply.add_answer(RR(qname, QTYPE.A, rdata=A(src), ttl=0))
            reply.add_answer(RR(qname, QTYPE.A, rdata=A(dst), ttl=0))
        
        elif option == "rd":  # Random
            answer_ip = random.choice([src, dst])
            reply.add_answer(RR(qname, QTYPE.A, rdata=A(answer_ip), ttl=0))
        
        else:
            # Return NXDOMAIN for invalid options
            reply.header.rcode = RCODE.NXDOMAIN
        
        return reply

if __name__ == "__main__":

    # DNS server configuration
    resolver = RebindResolver(rebinder_dns="yourdomain.com")
    server = DNSServer(resolver, port=53, address="0.0.0.0", tcp=False)
    
    print("Starting Rebind DNS server on port 53...")
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nDNS server stopped.")
