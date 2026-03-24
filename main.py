import typer
from paper_search import literature_search as lit_search

app = typer.Typer()

@app.command()
def search_for_papers(variant:str, max_results:int, min_date:str='2023', max_date:str=None, download_dir:str='genomic_papers'):
    lit_search.run_miner(variant, max_results, min_date, max_date, download_dir)

if __name__ == "__main__":
    app()
