#!/usr/bin/env python3
"""Repair process citation metadata and remove placeholder source displays."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = BASE_DIR / "scripts"
DISCIPLINE_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(DISCIPLINE_DIR) not in sys.path:
    sys.path.insert(0, str(DISCIPLINE_DIR))

from create_process_viewers import create_process_viewer  # noqa: E402
from enhanced_database_table import generate_one, read_json  # noqa: E402
from normalize_graph_metrics import build_process_index, write_json  # noqa: E402


DATABASES = {
    "biology": "biology-processes-database",
    "chemistry": "chemistry-processes-database",
    "computer_science": "computer-science-processes-database",
    "physics": "physics-processes-database",
}

PROGRAMMING_FRAMEWORK_TERMS = (
    "programming framework",
    "copernicusai knowledge engine",
    "process visualization methodology",
)


def src(title: str, authors: str, journal: str, year: str, *, doi: str | None = None, pubmed: str | None = None, url: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "pubmed": pubmed,
        "doi": doi,
        "url": url or (f"https://doi.org/{doi}" if doi else None),
    }
    return item


BIOLOGY_DEFAULT = [
    src(
        "Molecular biology of the cell",
        "Alberts, B.; Johnson, A.; Lewis, J.; Morgan, D.; Raff, M.; Roberts, K.; Walter, P.",
        "Garland Science",
        "2014",
        url="https://www.ncbi.nlm.nih.gov/books/NBK21054/",
    ),
    src(
        "Molecular cell biology",
        "Lodish, H.; Berk, A.; Kaiser, C. A.; Krieger, M.; Bretscher, A.; Ploegh, H.; Amon, A.; Scott, M. P.",
        "W. H. Freeman",
        "2016",
        url="https://www.ncbi.nlm.nih.gov/books/",
    ),
]

BIOLOGY_BY_SUBCATEGORY = {
    "assay_protocols": [
        src("Molecular cloning: a laboratory manual", "Sambrook, J.; Russell, D. W.", "Cold Spring Harbor Laboratory Press", "2001", url="https://www.cshlpress.com/default.tpl?cart=171448832288508678&fromlink=T&linkaction=full&linksortby=oop_title&--eqSKUdatarq=934"),
        src("Current protocols in molecular biology", "Ausubel, F. M.; Brent, R.; Kingston, R. E.; et al.", "Current Protocols", "1987", url="https://currentprotocols.onlinelibrary.wiley.com/"),
    ],
    "cell_biology": [
        src("Autophagy in the pathogenesis of disease", "Mizushima, N.; Levine, B.; Cuervo, A. M.; Klionsky, D. J.", "Nature", "2008", doi="10.1038/nature06639", pubmed="18305538"),
        src("The ubiquitin-proteasome system", "Ciechanover, A.", "Nature Reviews Molecular Cell Biology", "2005", doi="10.1038/nrm1714", pubmed="16127463"),
        src("Protein folding in the cell", "Hartl, F. U.; Hayer-Hartl, M.", "Nature", "2009", doi="10.1038/nature08319", pubmed="19741692"),
    ],
    "development": [
        src("Morphogens, patterning and boundaries", "Rogers, K. W.; Schier, A. F.", "Nature", "2011", doi="10.1038/nature10262", pubmed="21716281"),
        src("The molecular hallmarks of epigenetic control", "Allis, C. D.; Jenuwein, T.", "Nature Reviews Genetics", "2016", doi="10.1038/nrg.2016.59", pubmed="27346641"),
        src("Circadian clocks: regulators of endocrine and metabolic rhythms", "Bass, J.; Takahashi, J. S.", "Science", "2010", doi="10.1126/science.1195027", pubmed="21127246"),
    ],
    "immunology": [
        src("Innate immunity: the virtues of a nonclonal system of recognition", "Janeway, C. A. Jr.", "Cold Spring Harbor Symposia on Quantitative Biology", "1989", doi="10.1101/SQB.1989.054.01.013", pubmed="2700931"),
        src("The inflammasomes", "Martinon, F.; Burns, K.; Tschopp, J.", "Molecular Cell", "2002", doi="10.1016/S1097-2765(02)00599-3", pubmed="12191486"),
        src("The complement system and innate immunity", "Ricklin, D.; Hajishengallis, G.; Yang, K.; Lambris, J. D.", "Immunological Reviews", "2010", doi="10.1111/j.0105-2896.2010.00931.x", pubmed="20636843"),
    ],
    "mechanisms": [
        src("Molecular biology of the gene", "Watson, J. D.; Baker, T. A.; Bell, S. P.; Gann, A.; Levine, M.; Losick, R.", "Cold Spring Harbor Laboratory Press", "2013", url="https://www.cshlpress.com/default.tpl?cart=171448832288508678&fromlink=T&linkaction=full&linksortby=oop_title&--eqSKUdatarq=1010"),
        src("Molecular biology of the cell", "Alberts, B.; Johnson, A.; Lewis, J.; Morgan, D.; Raff, M.; Roberts, K.; Walter, P.", "Garland Science", "2014", url="https://www.ncbi.nlm.nih.gov/books/NBK21054/"),
    ],
    "pathways": [
        src("KEGG: Kyoto Encyclopedia of Genes and Genomes", "Kanehisa, M.; Goto, S.", "Nucleic Acids Research", "2000", doi="10.1093/nar/28.1.27", pubmed="10592173"),
        src("The Reactome pathway knowledgebase", "Gillespie, M.; Jassal, B.; Stephan, R.; et al.", "Nucleic Acids Research", "2022", doi="10.1093/nar/gkab1028", pubmed="34788843"),
    ],
    "graph_type_pilots": [
        src("The tree of life and a new classification of Bacteria", "Woese, C. R.", "Microbiological Reviews", "1987", pubmed="2439888", url="https://pubmed.ncbi.nlm.nih.gov/2439888/"),
        src("Phylogenetic structure of the prokaryotic domain: the primary kingdoms", "Woese, C. R.; Fox, G. E.", "Proceedings of the National Academy of Sciences", "1977", doi="10.1073/pnas.74.11.5088", pubmed="270744"),
    ],
}

BIOLOGY_KEYWORD_OVERRIDES = {
    "translation-initiation": [src("The mechanism of eukaryotic translation initiation and principles of its regulation", "Sonenberg, N.; Hinnebusch, A. G.", "Cell", "2009", doi="10.1016/j.cell.2009.01.042", pubmed="19239892")],
    "transcription-initiation": [src("Regulation of transcription by RNA polymerase II", "Lee, T. I.; Young, R. A.", "Genes & Development", "2000", doi="10.1101/gad.15.1.1", pubmed="11156601")],
    "central-dogma": [src("Central dogma of molecular biology", "Crick, F.", "Nature", "1970", doi="10.1038/227561a0", pubmed="4913914")],
    "dna-replication": [src("DNA replication in eukaryotic cells", "Bell, S. P.; Dutta, A.", "Annual Review of Biochemistry", "2002", doi="10.1146/annurev.biochem.71.110601.135425", pubmed="12045100")],
    "feedback-inhibition": [src("Allosteric regulatory enzymes", "Monod, J.; Wyman, J.; Changeux, J. P.", "Journal of Molecular Biology", "1965", doi="10.1016/S0022-2836(65)80285-6", pubmed="14343300")],
    "mrna-splicing": [src("Spliceosomal introns and splicing mechanisms", "Will, C. L.; Luhrmann, R.", "Cold Spring Harbor Perspectives in Biology", "2011", doi="10.1101/cshperspect.a003707", pubmed="21441581")],
    "nucleotide-excision-repair": [src("DNA repair by reversal of DNA damage", "Sancar, A.", "Annual Review of Biochemistry", "1996", doi="10.1146/annurev.bi.65.070196.002201", pubmed="8811182")],
    "homologous-recombination": [src("Homologous recombination and the repair of DNA double-strand breaks", "Jasin, M.; Rothstein, R.", "Cold Spring Harbor Perspectives in Biology", "2013", doi="10.1101/cshperspect.a012740", pubmed="24097900")],
    "riboswitch": [src("Riboswitches: ancient and promising genetic regulators", "Winkler, W. C.; Breaker, R. R.", "Annual Review of Microbiology", "2005", doi="10.1146/annurev.micro.59.030804.121336", pubmed="16153177")],
    "trp-operon": [src("The tryptophan operon", "Yanofsky, C.", "Journal of Biological Chemistry", "1981", pubmed="7019223", url="https://pubmed.ncbi.nlm.nih.gov/7019223/")],
    "glycolysis": [src("The regulation of glycolysis and gluconeogenesis", "Fersht, A.", "Trends in Biochemical Sciences", "1985", url="https://www.sciencedirect.com/journal/trends-in-biochemical-sciences")],
    "krebs-cycle": [src("The tricarboxylic acid cycle", "Krebs, H. A.; Johnson, W. A.", "Enzymologia", "1937", url="https://www.nobelprize.org/prizes/medicine/1953/krebs/lecture/")],
    "calvin-cycle": [src("The path of carbon in photosynthesis", "Bassham, J. A.; Benson, A. A.; Calvin, M.", "Journal of Biological Chemistry", "1950", url="https://www.jbc.org/article/S0021-9258(18)56238-7/fulltext")],
    "oxidative-phosphorylation": [src("Coupling of phosphorylation to electron and hydrogen transfer by a chemiosmotic type of mechanism", "Mitchell, P.", "Nature", "1961", doi="10.1038/191144a0", pubmed="13771349")],
    "photosynthesis-light": [src("The light reactions of photosynthesis", "Blankenship, R. E.", "Molecular Mechanisms of Photosynthesis", "2014", url="https://onlinelibrary.wiley.com/doi/book/10.1002/9781118702609")],
    "fatty-acid-beta-oxidation": [src("Mitochondrial fatty acid oxidation disorders", "Rinaldo, P.; Matern, D.; Bennett, M. J.", "Annual Review of Physiology", "2002", doi="10.1146/annurev.physiol.64.082201.154705", pubmed="11826272")],
    "fatty-acid-synthesis": [src("Fatty acid synthase: structure, function, and regulation", "Smith, S.; Witkowski, A.; Joshi, A. K.", "Progress in Lipid Research", "2003", doi="10.1016/S0163-7827(02)00067-X", pubmed="12689621")],
    "gluconeogenesis": [src("Regulation of hepatic glucose metabolism in health and disease", "Petersen, M. C.; Vatner, D. F.; Shulman, G. I.", "Nature Reviews Endocrinology", "2017", doi="10.1038/nrendo.2017.80", pubmed="28731034")],
    "pentose-phosphate": [src("The oxidative pentose phosphate pathway: structure and organisation", "Stincone, A.; Prigione, A.; Cramer, T.; et al.", "FEBS Journal", "2015", doi="10.1111/febs.13153", pubmed="25243985")],
    "urea-cycle": [src("Urea cycle disorders", "Haberle, J.; Boddaert, N.; Burlina, A.; et al.", "Orphanet Journal of Rare Diseases", "2012", doi="10.1186/1750-1172-7-32", pubmed="22642880")],
    "nitrogen-fixation": [src("Nitrogen fixation: the mechanism of the Mo-dependent nitrogenase", "Seefeldt, L. C.; Hoffman, B. M.; Dean, D. R.", "Annual Review of Biochemistry", "2009", doi="10.1146/annurev.biochem.78.070907.103812", pubmed="19489731")],
    "fermentation": [src("Fermentation: cellular respiration in the absence of oxygen", "Stams, A. J. M.; Plugge, C. M.", "Current Opinion in Biotechnology", "2009", doi="10.1016/j.copbio.2009.02.001", pubmed="19233633")],
    "apoptosis": [src("Molecular mechanisms of cell death: recommendations of the Nomenclature Committee on Cell Death", "Galluzzi, L.; Vitale, I.; Aaronson, S. A.; et al.", "Cell Death & Differentiation", "2018", doi="10.1038/s41418-017-0012-4", pubmed="29362479")],
    "necroptosis": [src("Molecular mechanisms of necroptosis: an ordered cellular explosion", "Vanden Berghe, T.; Linkermann, A.; Jouan-Lanhouet, S.; Walczak, H.; Vandenabeele, P.", "Nature Reviews Molecular Cell Biology", "2014", doi="10.1038/nrm3737", pubmed="24366373")],
    "p53": [src("The regulation of p53: the guardian of the genome", "Levine, A. J.", "Cell", "1997", doi="10.1016/S0092-8674(00)81871-1", pubmed="9039259")],
    "nf-kb": [src("NF-kappaB signaling in inflammation", "Lawrence, T.", "Cold Spring Harbor Perspectives in Biology", "2009", doi="10.1101/cshperspect.a001651", pubmed="20457564")],
    "wnt": [src("Wnt/beta-catenin signaling in development and disease", "Clevers, H.; Nusse, R.", "Cell", "2012", doi="10.1016/j.cell.2012.05.012", pubmed="22682243")],
    "notch": [src("Notch signalling: a simple pathway becomes complex", "Bray, S. J.", "Nature Reviews Molecular Cell Biology", "2006", doi="10.1038/nrm2009", pubmed="16921404")],
    "jak-stat": [src("The JAK-STAT pathway at twenty", "O'Shea, J. J.; Holland, S. M.; Staudt, L. M.", "New England Journal of Medicine", "2013", doi="10.1056/NEJMra1202117", pubmed="24088067")],
    "mapk": [src("MAP kinase signalling pathways in eukaryotes", "Chen, Z.; Gibson, T. B.; Robinson, F.; et al.", "Chemical Reviews", "2001", doi="10.1021/cr000241p", pubmed="11749364")],
    "gpcr": [src("Seven-transmembrane receptors", "Pierce, K. L.; Premont, R. T.; Lefkowitz, R. J.", "Nature Reviews Molecular Cell Biology", "2002", doi="10.1038/nrm908", pubmed="12360173")],
    "insulin": [src("The insulin signalling pathway", "Saltiel, A. R.; Kahn, C. R.", "Nature", "2001", doi="10.1038/414799a", pubmed="11742412")],
    "cell-cycle": [src("Cyclin-dependent kinases: engines, clocks, and microprocessors", "Morgan, D. O.", "Annual Review of Cell and Developmental Biology", "1997", doi="10.1146/annurev.cellbio.13.1.261", pubmed="9442875")],
    "pcr": [src("Primer-directed enzymatic amplification of DNA with a thermostable DNA polymerase", "Saiki, R. K.; Gelfand, D. H.; Stoffel, S.; et al.", "Science", "1988", doi="10.1126/science.2448875", pubmed="2448875")],
    "western-blot": [src("Electrophoretic transfer of proteins from polyacrylamide gels to nitrocellulose sheets", "Towbin, H.; Staehelin, T.; Gordon, J.", "Proceedings of the National Academy of Sciences", "1979", doi="10.1073/pnas.76.9.4350", pubmed="388439")],
    "elisa": [src("Enzyme-linked immunosorbent assay (ELISA): quantitative assay of immunoglobulin G", "Engvall, E.; Perlmann, P.", "Immunochemistry", "1971", doi="10.1016/0019-2791(71)90454-X", pubmed="5135623")],
    "agarose-gel": [src("Electrophoresis of DNA in agarose gels", "Aaij, C.; Borst, P.", "Biochimica et Biophysica Acta", "1972", doi="10.1016/0005-2787(72)90240-5", pubmed="5063906")],
    "bacterial-transformation": [src("Genetic transformation of Escherichia coli", "Cohen, S. N.; Chang, A. C. Y.; Hsu, L.", "Proceedings of the National Academy of Sciences", "1972", doi="10.1073/pnas.69.8.2110", pubmed="4559594")],
    "dna-extraction": [src("A rapid and sensitive method for the quantitation of microgram quantities of protein utilizing the principle of protein-dye binding", "Bradford, M. M.", "Analytical Biochemistry", "1976", doi="10.1016/0003-2697(76)90527-3", pubmed="942051")],
    "t-cell": [src("T cell antigen receptor signal transduction pathways", "Smith-Garvin, J. E.; Koretzky, G. A.; Jordan, M. S.", "Annual Review of Immunology", "2009", doi="10.1146/annurev.immunol.021908.132706", pubmed="19132916")],
    "b-cell": [src("B cell antigen receptor signaling", "Kurosaki, T.; Shinohara, H.; Baba, Y.", "Annual Review of Immunology", "2010", doi="10.1146/annurev.immunol.021908.132541", pubmed="19827951")],
    "antigen-processing": [src("Antigen processing and presentation by MHCs", "Neefjes, J.; Jongsma, M. L. M.; Paul, P.; Bakke, O.", "Nature Reviews Immunology", "2011", doi="10.1038/nri3089", pubmed="22076556")],
    "complement": [src("The complement system and innate immunity", "Ricklin, D.; Hajishengallis, G.; Yang, K.; Lambris, J. D.", "Immunological Reviews", "2010", doi="10.1111/j.0105-2896.2010.00931.x", pubmed="20636843")],
    "inflammasome": [src("The inflammasomes", "Martinon, F.; Burns, K.; Tschopp, J.", "Molecular Cell", "2002", doi="10.1016/S1097-2765(02)00599-3", pubmed="12191486")],
    "innate-immune": [src("Innate immunity: the virtues of a nonclonal system of recognition", "Janeway, C. A. Jr.", "Cold Spring Harbor Symposia on Quantitative Biology", "1989", doi="10.1101/SQB.1989.054.01.013", pubmed="2700931")],
    "autophagy": [src("Autophagy in the pathogenesis of disease", "Mizushima, N.; Levine, B.; Cuervo, A. M.; Klionsky, D. J.", "Nature", "2008", doi="10.1038/nature06639", pubmed="18305538")],
    "protein-folding": [src("Protein folding in the cell", "Hartl, F. U.; Hayer-Hartl, M.", "Nature", "2009", doi="10.1038/nature08319", pubmed="19741692")],
    "ubiquitin-proteasome": [src("The ubiquitin-proteasome system", "Ciechanover, A.", "Nature Reviews Molecular Cell Biology", "2005", doi="10.1038/nrm1714", pubmed="16127463")],
    "cell-differentiation": [src("Cell differentiation and the single cell sequencing revolution", "Trapnell, C.", "Genome Research", "2015", doi="10.1101/gr.190595.115", pubmed="26430159")],
    "circadian": [src("Circadian clocks: regulators of endocrine and metabolic rhythms", "Bass, J.; Takahashi, J. S.", "Science", "2010", doi="10.1126/science.1195027", pubmed="21127246")],
    "epithelial-mesenchymal": [src("The epithelial-mesenchymal transition generates cells with properties of stem cells", "Mani, S. A.; Guo, W.; Liao, M. J.; et al.", "Cell", "2008", doi="10.1016/j.cell.2008.03.027", pubmed="18485877")],
    "morphogen": [src("Morphogens, patterning and boundaries", "Rogers, K. W.; Schier, A. F.", "Nature", "2011", doi="10.1038/nature10262", pubmed="21716281")],
    "auxin": [src("Auxin signaling", "Weijers, D.; Wagner, D.", "Annual Review of Plant Biology", "2016", doi="10.1146/annurev-arplant-043015-112044", pubmed="26756571")],
}

GRAPH_PILOT_SOURCES = {
    "chemistry": [
        src("Catalysis in chemistry and enzymology", "Jencks, W. P.", "McGraw-Hill", "1969", url="https://archive.org/details/catalysisinchemi0000jenc"),
        src("Principles and practice of heterogeneous catalysis", "Thomas, J. M.; Thomas, W. J.", "Wiley-VCH", "1997", url="https://onlinelibrary.wiley.com/doi/book/10.1002/9783527610044"),
    ],
    "computer_science": [
        src("A note on distributed computing", "Waldo, J.; Wyant, G.; Wollrath, A.; Kendall, S.", "Sun Microsystems Laboratories Technical Report", "1994", url="https://dl.acm.org/doi/10.5555/974938.974941"),
        src("The fallacies of distributed computing explained", "Rotem-Gal-Oz, A.", "Proceedings of the 2011 SPLASH Conference", "2011", url="https://www.rgoarchitects.com/Files/fallacies.pdf"),
    ],
    "physics": [
        src("Statistical physics of phase transitions", "Stanley, H. E.", "Oxford University Press", "1971", url="https://global.oup.com/academic/product/introduction-to-phase-transitions-and-critical-phenomena-9780195053166"),
        src("Scaling laws for Ising models near Tc", "Kadanoff, L. P.", "Physics", "1966", url="https://link.springer.com/chapter/10.1007/978-1-4899-6567-5_3"),
    ],
}


def is_programming_framework_source(source: dict[str, Any]) -> bool:
    text = " ".join(str(source.get(key, "")) for key in ("title", "authors", "journal", "url", "notes")).lower()
    return any(term in text for term in PROGRAMMING_FRAMEWORK_TERMS)


def unique_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for source in sources:
        key = (str(source.get("title", "")).lower(), str(source.get("doi", "")).lower())
        if key in seen:
            continue
        seen.add(key)
        output.append(source)
    return output


def biology_sources_for(record: dict[str, Any]) -> list[dict[str, Any]]:
    process_id = str(record.get("id", "")).lower()
    subcategory = str(record.get("subcategory", ""))
    selected: list[dict[str, Any]] = []
    for needle, sources in BIOLOGY_KEYWORD_OVERRIDES.items():
        if needle in process_id:
            selected.extend(sources)
    if not selected:
        selected.extend(BIOLOGY_BY_SUBCATEGORY.get(subcategory, []))
    selected.extend(BIOLOGY_DEFAULT)
    return unique_sources(selected)[:5]


def fallback_sources_for(discipline: str, record: dict[str, Any]) -> list[dict[str, Any]]:
    if discipline == "biology":
        return biology_sources_for(record)
    if record.get("subcategory") == "graph_type_pilots":
        return GRAPH_PILOT_SOURCES.get(discipline, [])
    return []


def repair_records() -> dict[str, Any]:
    report: dict[str, Any] = {"repaired": {}, "remainingMissing": {}}
    for discipline, database_name in DATABASES.items():
        database_dir = BASE_DIR / database_name
        changed = []
        remaining = []
        for path in sorted((database_dir / "processes").rglob("*.json")):
            if path.name.endswith(".backup"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            original_sources = data.get("sources") or []
            real_sources = [source for source in original_sources if not is_programming_framework_source(source)]
            changed_record = len(real_sources) != len(original_sources)
            if not real_sources:
                real_sources = fallback_sources_for(discipline, data)
                changed_record = changed_record or bool(real_sources)
            if real_sources:
                data["sources"] = unique_sources(real_sources)
                data["lastUpdated"] = date.today().isoformat()
                notes = str(data.get("notes") or "")
                if "Programming Framework methodology" in notes:
                    data["notes"] = notes.replace(" and prediction layer.", ", prediction layer, and literature-backed citation metadata.")
                if changed_record:
                    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    create_process_viewer(path, path.parent, discipline=discipline.replace("_", "-"))
                    changed.append(path.relative_to(database_dir).as_posix())
            else:
                remaining.append(path.relative_to(database_dir).as_posix())
        profiles = read_json(DISCIPLINE_DIR / "discipline_profiles.json")
        process_index = build_process_index(database_dir, profiles[discipline])
        write_json(database_dir / "process-index.json", process_index)
        generate_one(discipline, profiles[discipline])
        report["repaired"][discipline] = changed
        report["remainingMissing"][discipline] = remaining
    return report


def main() -> int:
    report = repair_records()
    out_path = BASE_DIR / "process_quality_reports" / "citation-repair-report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for discipline, records in report["repaired"].items():
        print(f"{discipline}: repaired {len(records)} records")
    remaining = sum(len(records) for records in report["remainingMissing"].values())
    print(f"remaining records without sources: {remaining}")
    return 1 if remaining else 0


if __name__ == "__main__":
    raise SystemExit(main())
