# repro-doctor report

<!-- Redacted example with illustrative repository values. -->

## Detected stack

- Stack: Node.js / TypeScript
- Package: example-node-service
- Runtime: Node.js 22
- Package manager: npm (package.json packageManager)
- Detection confidence: high
- Test command: `npm test`

## Changed files

- `Dockerfile`
- `Makefile`
- `README.repro-doctor.md`

## Verification

- `docker build -t repro-doctor-target-example-node .`
- `docker run --rm repro-doctor-target-example-node make test`

- Result: passed
- Retry count: 0

### Repair attempts

- (none)
