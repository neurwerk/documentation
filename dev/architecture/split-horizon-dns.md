# Selective Split-Horizon DNS

Selected Pods resolve public endpoint names to the cluster Traefik Service: Dify
and LibreChat use the Keycloak issuer, the Keycloak action-email Job checks that
issuer, and LibreChat uses the object-store endpoint.
These are DNS rewrites, not HTTP redirects; public URLs, TLS SNI, OIDC issuer
identity, and S3 signatures remain unchanged.

| Public endpoint | Internal DNS target |
| --- | --- |
| Keycloak issuer hostname | Traefik Service on TCP `443` |
| LibreChat object-store hostname | Traefik Service on TCP `443` |
