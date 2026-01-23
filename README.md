# Search-ADS

CLI tool for automating scientific paper citations in LaTeX documents using NASA ADS.

## Features

- Search for papers using NASA ADS API
- Automatically fill empty `\cite{}` in LaTeX files
- Build and maintain a local paper database
- Expand citation graphs (references and citations)
- Generate BibTeX entries automatically

## Installation

```bash
pip install -e .
```

## Configuration

Create a `.env` file with your API keys:

```
ADS_API_KEY=your_ads_api_key_here
```

Get your ADS API key at: https://ui.adsabs.harvard.edu/user/settings/token

## Usage

### Seed the database with a paper

```bash
search-ads seed "https://ui.adsabs.harvard.edu/abs/2023ApJ...XXX"
search-ads seed 2023ApJ...XXX --expand --hops 2
```

### Search for papers

```bash
search-ads find --context "dark matter halo mass function"
```

### Fill citations in LaTeX

```bash
search-ads fill --bibcode "2023ApJ...XXX" --tex-file paper.tex --line 42 --column 10
```

### View database status

```bash
search-ads status
search-ads list-papers
```

## License

MIT
