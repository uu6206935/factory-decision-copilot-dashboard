# License Strategy

The project-specific orchestration, manufacturing schema mapping, investigation workflow and customer adapters can be kept proprietary.

Infrastructure dependencies may remain separate OSS services/libraries under their own licenses. Prefer permissive dependencies (MIT/Apache-2.0/BSD) when alternatives are equivalent, and keep required attribution/NOTICE files.

Before a commercial release:
1. generate an SBOM for the exact build;
2. scan transitive dependencies and container images;
3. identify copyleft/network-copyleft obligations;
4. keep third-party notices with the distribution;
5. have counsel approve the customer EULA/SaaS terms and OSS compliance process.

This file is product-engineering guidance, not legal advice.
