# repro-doctor report

<!-- Redacted example with illustrative repository values. -->

## Detected stack

- Stack: Python
- Package: example-python-service
- Runtime: Python 3.12
- Detection confidence: high
- Test command: `make test`

## Changed files

- `Dockerfile`
- `Makefile`
- `.python-version`
- `README.repro-doctor.md`

## Verification

- `docker build -t repro-doctor-target-example-python .`
- `docker run --rm repro-doctor-target-example-python make test`

- Result: passed
- Retry count: 0

### Repair attempts

- (none)
