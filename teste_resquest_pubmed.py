import re
import xml.etree.ElementTree as ET
import requests


def search_pubmed(query, retmax=10):
    """Busca IDs de artigos no PubMed. Retorna lista de IDs (strings). retmax = máximo de resultados."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query.strip() or "medicine",
        "retmax": max(1, min(retmax, 20)),
        "retmode": "json"
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        result = data.get("esearchresult") or {}
        ids = result.get("idlist") or []
        return ids if isinstance(ids, list) else []
    except (requests.RequestException, ValueError, KeyError):
        return []


def fetch_article_details(ids):
    """Busca detalhes dos artigos por ID. ids deve ser lista de strings."""
    if not ids:
        return ""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(str(i) for i in ids),
        "retmode": "xml"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.text or ""
    except (requests.RequestException, ValueError):
        return ""


def _text(el):
    """Texto do elemento, ou string vazia se None."""
    if el is None:
        return ""
    return (el.text or "") + "".join(ET.tostring(c, encoding="unicode", method="text") for c in el)


def _clean(text):
    """Remove entidades HTML e espaços extras."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)
    return text.strip()


def _find_recursive(parent, local_name):
    """Encontra primeiro descendente com local name."""
    if parent is None:
        return None
    name = parent.tag.split("}")[-1] if parent.tag and "}" in parent.tag else parent.tag
    if name == local_name:
        return parent
    for c in parent:
        found = _find_recursive(c, local_name)
        if found is not None:
            return found
    return None


def _find_all_recursive(parent, local_name):
    """Lista todos os descendentes com local name."""
    if parent is None:
        return []
    out = []
    name = parent.tag.split("}")[-1] if parent.tag and "}" in parent.tag else parent.tag
    if name == local_name:
        out.append(parent)
    for c in parent:
        out.extend(_find_all_recursive(c, local_name))
    return out


def parse_articles(xml_text):
    """Extrai lista de artigos do XML do PubMed."""
    if not (xml_text and xml_text.strip()):
        return []
    root = ET.fromstring(xml_text)
    articles = []
    for art in _find_all_recursive(root, "PubmedArticle"):
        art_el = _find_recursive(art, "Article")
        if art_el is None:
            continue
        # PMID
        pmid_el = _find_recursive(art, "PMID")
        pmid = pmid_el.text if pmid_el is not None and pmid_el.text else "—"
        # Título
        title_el = _find_recursive(art_el, "ArticleTitle")
        title = _clean(_text(title_el)) if title_el is not None else "—"
        # Journal
        journal_el = _find_recursive(art_el, "Journal")
        journal = "—"
        if journal_el is not None:
            t = _find_recursive(journal_el, "Title")
            if t is not None and t.text:
                journal = t.text.strip()
        # Data (ano)
        pub_date = _find_recursive(art_el, "PubDate")
        year = (pub_date.text or "").strip() if pub_date is not None and pub_date.text else "—"
        # DOI
        doi = "—"
        for eid in _find_all_recursive(art, "ELocationID"):
            if eid.get("EIdType") == "doi" and eid.text:
                doi = eid.text.strip()
                break
        if doi == "—":
            for aid in _find_all_recursive(art, "ArticleId"):
                if aid.get("IdType") == "doi" and aid.text:
                    doi = aid.text.strip()
                    break
        # Full text links: PubMed, PMC (se houver), DOI (se houver)
        full_text_links = []
        full_text_links.append(("PubMed", f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"))
        pmc_id = None
        for aid in _find_all_recursive(art, "ArticleId"):
            if aid.get("IdType") == "pmc" and aid.text:
                pmc_id = aid.text.strip()
                if not pmc_id.upper().startswith("PMC"):
                    pmc_id = f"PMC{pmc_id}"
                full_text_links.append(("PubMed Central (full text)", f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"))
                break
        if doi != "—":
            full_text_links.append(("DOI", f"https://doi.org/{doi}"))
        # Autores
        authors = []
        for a in _find_all_recursive(art_el, "Author"):
            last = _find_recursive(a, "LastName")
            fore = _find_recursive(a, "ForeName")
            if last is not None and last.text:
                name = last.text
                if fore is not None and fore.text:
                    name = f"{fore.text} {name}"
                authors.append(name)
        authors_str = "; ".join(authors[:5])
        if len(authors) > 5:
            authors_str += f" et al. (+{len(authors) - 5})"
        if not authors_str:
            authors_str = "—"
        # Abstract
        abstract = ""
        for ab in _find_all_recursive(art_el, "AbstractText"):
            abstract = _clean(_text(ab))
            if abstract:
                break
        if not abstract:
            abstract = "(sem resumo)"
        if len(abstract) > 400:
            abstract = abstract[:397] + "..."
        articles.append({
            "pmid": pmid,
            "title": title,
            "journal": journal,
            "year": year,
            "doi": doi,
            "authors": authors_str,
            "abstract": abstract,
            "full_text_links": full_text_links,
        })
    return articles


def print_articles(articles):
    """Imprime os artigos em formato legível."""
    sep = "=" * 72
    for i, a in enumerate(articles, 1):
        print(sep)
        print(f"  [{i}] PMID: {a['pmid']}  |  {a['journal']}  ({a['year']})")
        print(sep)
        print(f"  Título: {a['title']}")
        print(f"  DOI: {a['doi']}")
        print(f"  Autores: {a['authors']}")
        if a.get("full_text_links"):
            print("  Full text links:")
            for label, url in a["full_text_links"]:
                print(f"    • {label}: {url}")
        print()
        print(f"  Resumo: {a['abstract']}")
        print()


def main():
    query = input("Digite um tema médico: ").strip()
    if not query:
        query = "diabetes"
        print(f"(usando busca padrão: {query})\n")

    ids = search_pubmed(query)
    print("\nIDs encontrados:", ", ".join(ids))

    if not ids:
        print("Nenhum resultado encontrado.")
        return

    print("\nBuscando detalhes dos artigos...\n")
    xml_text = fetch_article_details(ids)
    articles = parse_articles(xml_text)
    print_articles(articles)
    print("=" * 72)


if __name__ == "__main__":
    main()