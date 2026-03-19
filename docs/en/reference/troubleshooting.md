# Troubleshooting

## Viewing Logs

```bash
# Docker
docker compose logs -f                    # All services
docker compose logs -f controller         # Specific service
docker compose logs --tail=100 controller # Recent logs
docker compose logs | grep ERROR          # Errors only

# Kubernetes
kubectl logs -l app=netpulse,component=controller --tail=100
kubectl describe pod <pod-name>
```

Log format: `[timestamp] [PID] [LEVEL] [module|file:line] - message`

## Common Issues

### Service Startup

**Container won't start:**
```bash
sudo systemctl status docker     # Docker running?
sudo netstat -tlnp | grep :9000  # Port in use?
docker compose logs              # Check error details
```

**API Key problems:**
```bash
cat .env | grep NETPULSE_SERVER__API_KEY  # Check current key
# Regenerate if needed:
docker compose down
rm .env
bash ./scripts/setup_env.sh generate
docker compose up -d
```

### Connection Issues

**Device connection timeout:**

- Verify network reachability (`ping`, `ssh`)
- Check `device_type` is correct
- Increase timeouts:

```json
{
  "connection_args": {
    "host": "192.168.1.1",
    "timeout": 60,
    "read_timeout": 120
  }
}
```

**SSH authentication failure:**

- Test manually: `ssh admin@192.168.1.1`
- Check if `secret` (enable password) is needed
- Verify `device_type` matches the actual device

### API Issues

**403 Forbidden** — API key missing or invalid. Check `X-API-KEY` header value.

**400 Bad Request** — Missing required fields. Check request body against [API docs](../api/api-overview.md).

**Task failed** — Query job details via `/job?id=xxx` and check the error in the result.

### Performance

**Slow execution:**

- Scale workers: `docker compose up --scale node-worker=3 -d`
- Use Pinned queue for repeated operations on same device
- Increase `read_timeout` for slow devices

**High memory:**

- Check usage: `docker stats`
- Reduce `pinned_per_node` in config
- Lower `result_ttl` to free Redis memory

### Redis Connection

```bash
# Docker
docker compose ps redis
docker compose logs redis
docker compose restart redis

# Kubernetes
kubectl get pods -l app=redis
kubectl exec -it redis-nodes-0 -- redis-cli -a $REDIS_PASSWORD ping
```

## Diagnosis Steps

1. **View logs** of the relevant service
2. **Check configuration** — `.env`, `config/config.yaml`
3. **Test connectivity** — network, device, Redis
4. **Check resources** — `docker stats` or `kubectl top pods`
5. **Submit issue** on [GitHub](https://github.com/scitix/netpulse/issues) with logs and environment info
