# SD-WAN Test Topology

This directory contains containerlab topology files for integration testing ORBIT against real SD-WAN infrastructure.

## Topology: sdwan-simple

A minimal SD-WAN setup with:
- 1x vManage (manager)
- 1x vSmart (controller)
- 1x vBond (validator)
- 1x C8000v Edge (cedge)

### Quick Start

1. **Deploy the topology:**
   ```bash
   cd tests/topology
   sudo containerlab deploy -t sdwan-simple.clab.yml
   ```

2. **Check status:**
   ```bash
   sudo containerlab inspect -t sdwan-simple.clab.yml
   ```

3. **Access devices:**
   - vManage: https://172.20.20.3 (admin/admin)
   - Console access: `telnet <ip> 5000`
   - SSH: Currently limited due to SD-WAN controller mode restrictions

4. **Run ORBIT onboarding:**
   ```bash
   orbit onboard tests/topology/orbit-devices.yaml
   ```

5. **Destroy topology:**
   ```bash
   sudo containerlab destroy -t sdwan-simple.clab.yml
   ```

## Files

- `sdwan-simple.clab.yml` - Containerlab topology definition
- `orbit-devices.yaml` - ORBIT device inventory for this topology
- `manager-config.xml` - vManage bootstrap configuration
- `controller-config.xml` - vSmart bootstrap configuration
- `validator-config.xml` - vBond bootstrap configuration
- `cedge-bootstrap.cfg` - C8000v bootstrap configuration (cloud-init)

## Notes

- The topology uses vrnetlab images (must be built separately)
- Devices boot in SD-WAN controller mode
- SSH access is limited until devices are fully onboarded
- Use console access (port 5000) for troubleshooting
- Generated containerlab files (clab-*/) are gitignored

## Integration Testing

Use this topology for integration tests:

```python
# tests/integration/test_real_onboarding.py
import pytest
import os

@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("RUN_INTEGRATION_TESTS"),
                    reason="Set RUN_INTEGRATION_TESTS=1 to run")
def test_onboard_real_topology():
    from sdwan_orbit import Orbit
    orch = Orbit.from_file("tests/topology/orbit-devices.yaml")
    results = orch.onboard()
    assert len(results) > 0
```

Run integration tests:
```bash
RUN_INTEGRATION_TESTS=1 pytest tests/integration/ -v
```
