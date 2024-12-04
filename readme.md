# lilbro-pipelines

This repository contains code for [Open-WebUI](https://github.com/open-webui) plugins.

## Imported Plugins

- [safe-code-execution](https://github.com/EtiennePerot/safe-code-execution)

### Importing open-webui libraries

This repo uses the `PYTHONPATH` environment variable to import libraries from the `open-webui` repository. 

Run the following command and update the paths for your local copies of the repositories:

```bash
cp .env.example .env
```

This will be loaded automatically in VSCode. See the [settings.json](.vscode/settings.json) file for more details.