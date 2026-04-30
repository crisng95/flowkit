# Worker Lane Directory Layout

Each worker VM runs one lane.

```text
/srv/flowkit/
└── lane-XX/
    ├── chrome-profile/
    ├── extension/
    ├── runtime/
    │   ├── flow_agent.db
    │   └── output/
    ├── work/
    ├── logs/
    ├── env/
    │   ├── lane.env
    │   └── account.env
    └── scripts/
        ├── start-chrome.sh
        ├── start-agent.sh
        ├── lane-runner.sh
        └── upload-artifacts.sh
```

Rules:

- `chrome-profile/` is per account, never shared
- `runtime/` is per lane, never shared
- `work/` is scratch space for downloads and concat staging
- `logs/` is rotated locally
