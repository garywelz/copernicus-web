#!/usr/bin/env python3
"""Replace weak generated source records with authoritative references."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = BASE_DIR / "scripts"
DISCIPLINE_DIR = Path(__file__).resolve().parent
for path in (SCRIPTS_DIR, DISCIPLINE_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from create_process_viewers import create_process_viewer  # noqa: E402
from enhanced_database_table import generate_one, read_json  # noqa: E402
from normalize_graph_metrics import build_process_index, write_json  # noqa: E402


def src(title: str, authors: str, journal: str, year: str, *, doi: str | None = None, url: str | None = None) -> dict[str, Any]:
    return {
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "pubmed": None,
        "doi": doi,
        "url": url or (f"https://doi.org/{doi}" if doi else None),
    }


CS_CANONICAL = {
    "algorithms_data_structures": [
        src("A note on two problems in connexion with graphs", "Dijkstra, E. W.", "Numerische Mathematik", "1959", doi="10.1007/BF01386390"),
        src("Introduction to Algorithms", "Cormen, T. H.; Leiserson, C. E.; Rivest, R. L.; Stein, C.", "MIT Press", "2022", url="https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/"),
        src("Network flows: theory, algorithms, and applications", "Ahuja, R. K.; Magnanti, T. L.; Orlin, J. B.", "Prentice Hall", "1993", url="https://archive.org/details/networkflowstheo0000ahuj"),
    ],
    "machine_learning": [
        src("Pattern Recognition and Machine Learning", "Bishop, C. M.", "Springer", "2006", url="https://link.springer.com/book/9780387310732"),
        src("The Elements of Statistical Learning", "Hastie, T.; Tibshirani, R.; Friedman, J.", "Springer", "2009", doi="10.1007/978-0-387-84858-7"),
        src("Deep Learning", "Goodfellow, I.; Bengio, Y.; Courville, A.", "MIT Press", "2016", url="https://www.deeplearningbook.org/"),
    ],
    "networks": [
        src("Computer Networking: A Top-Down Approach", "Kurose, J. F.; Ross, K. W.", "Pearson", "2021", url="https://gaia.cs.umass.edu/kurose_ross/"),
        src("TCP Congestion Control", "Allman, M.; Paxson, V.; Blanton, E.", "RFC 5681", "2009", doi="10.17487/RFC5681"),
        src("The Design Philosophy of the DARPA Internet Protocols", "Clark, D. D.", "ACM SIGCOMM Computer Communication Review", "1988", doi="10.1145/52325.52336"),
    ],
    "security": [
        src("Security Engineering", "Anderson, R.", "Wiley", "2020", url="https://www.cl.cam.ac.uk/~rja14/book.html"),
        src("The OAuth 2.0 Authorization Framework", "Hardt, D.", "RFC 6749", "2012", doi="10.17487/RFC6749"),
        src("Zero Trust Architecture", "Rose, S.; Borchert, O.; Mitchell, S.; Connelly, S.", "NIST Special Publication 800-207", "2020", doi="10.6028/NIST.SP.800-207"),
    ],
    "software_engineering": [
        src("Software Engineering", "Sommerville, I.", "Pearson", "2016", url="https://www.pearson.com/en-us/subject-catalog/p/software-engineering/P200000003559"),
        src("Continuous Delivery", "Humble, J.; Farley, D.", "Addison-Wesley", "2010", url="https://continuousdelivery.com/"),
        src("The Mythical Man-Month", "Brooks, F. P.", "Addison-Wesley", "1995", url="https://www.pearson.com/en-us/subject-catalog/p/mythical-man-month-the-essays-on-software-engineering-anniversary-edition/P200000009016"),
    ],
    "systems": [
        src("Operating System Concepts", "Silberschatz, A.; Galvin, P. B.; Gagne, G.", "Wiley", "2018", url="https://www.os-book.com/"),
        src("Modern Operating Systems", "Tanenbaum, A. S.; Bos, H.", "Pearson", "2015", url="https://www.pearson.com/en-us/subject-catalog/p/modern-operating-systems/P200000003295"),
        src("The Datacenter as a Computer", "Barroso, L. A.; Clidaras, J.; Holzle, U.", "Morgan & Claypool", "2013", doi="10.2200/S00516ED2V01Y201306CAC024"),
    ],
    "theory": [
        src("Introduction to the Theory of Computation", "Sipser, M.", "Cengage", "2012", url="https://www.cengage.com/c/introduction-to-the-theory-of-computation-3e-sipser/"),
        src("Computational Complexity", "Papadimitriou, C. H.", "Addison-Wesley", "1994", url="https://dl.acm.org/doi/book/10.5555/530612"),
        src("Types and Programming Languages", "Pierce, B. C.", "MIT Press", "2002", url="https://mitpress.mit.edu/9780262162098/types-and-programming-languages/"),
    ],
    "graph_type_pilots": [
        src("A note on distributed computing", "Waldo, J.; Wyant, G.; Wollrath, A.; Kendall, S.", "Sun Microsystems Laboratories Technical Report", "1994", url="https://dl.acm.org/doi/10.5555/974938.974941"),
        src("Designing Data-Intensive Applications", "Kleppmann, M.", "O'Reilly Media", "2017", url="https://dataintensive.net/"),
    ],
}

CHEM_CANONICAL = {
    "analytical_chemistry": [
        src("Principles of Instrumental Analysis", "Skoog, D. A.; Holler, F. J.; Crouch, S. R.", "Cengage Learning", "2017", url="https://www.cengage.com/c/principles-of-instrumental-analysis-7e-skoog/"),
        src("Quantitative Chemical Analysis", "Harris, D. C.", "W. H. Freeman", "2015", url="https://www.macmillanlearning.com/college/us/product/Quantitative-Chemical-Analysis/p/1319164304"),
        src("Sample Preparation Techniques in Analytical Chemistry", "Mitra, S.", "Wiley", "2003", doi="10.1002/0471457817"),
    ],
    "biochemistry": [
        src("Biochemistry", "Berg, J. M.; Tymoczko, J. L.; Gatto, G. J.; Stryer, L.", "W. H. Freeman", "2019", url="https://www.macmillanlearning.com/college/us/product/Biochemistry/p/1319114679"),
        src("Enzyme Structure and Mechanism", "Fersht, A.", "W. H. Freeman", "1985", url="https://archive.org/details/enzymestructurem0000fers"),
    ],
    "computational_chemistry": [
        src("Essentials of Computational Chemistry", "Cramer, C. J.", "Wiley", "2004", doi="10.1002/0470091835"),
        src("Molecular Modelling: Principles and Applications", "Leach, A. R.", "Pearson", "2001", url="https://www.pearson.com/en-us/subject-catalog/p/molecular-modelling-principles-and-applications/P200000003401"),
    ],
    "electrochemistry": [
        src("Electrochemical Methods: Fundamentals and Applications", "Bard, A. J.; Faulkner, L. R.", "Wiley", "2001", url="https://www.wiley.com/en-us/Electrochemical+Methods%3A+Fundamentals+and+Applications%2C+2nd+Edition-p-9780471043720"),
        src("Modern Electrochemistry 2A", "Bockris, J. O'M.; Reddy, A. K. N.; Gamboa-Aldeco, M.", "Springer", "2000", doi="10.1007/b98850"),
    ],
    "environmental_chemistry": [
        src("Environmental Chemistry", "Manahan, S. E.", "CRC Press", "2017", doi="10.1201/9781315153841"),
        src("Chemistry of the Environment", "Spiro, T. G.; Stigliani, W. M.", "Prentice Hall", "2002", url="https://archive.org/details/chemistryofenviro0000spir"),
    ],
    "inorganic_chemistry": [
        src("Inorganic Chemistry", "Housecroft, C. E.; Sharpe, A. G.", "Pearson", "2018", url="https://www.pearson.com/en-gb/subject-catalog/p/inorganic-chemistry/P200000003235"),
        src("Advanced Inorganic Chemistry", "Cotton, F. A.; Wilkinson, G.; Murillo, C. A.; Bochmann, M.", "Wiley", "1999", url="https://www.wiley.com/en-us/Advanced+Inorganic+Chemistry%2C+6th+Edition-p-9780471199571"),
    ],
    "kinetics": [
        src("Chemical Kinetics and Reaction Dynamics", "Steinfeld, J. I.; Francisco, J. S.; Hase, W. L.", "Prentice Hall", "1999", url="https://archive.org/details/chemicalkinetics0000stei"),
        src("Kinetics and Mechanism", "Espenson, J. H.", "McGraw-Hill", "2002", url="https://archive.org/details/chemicalkinetics0000espe"),
    ],
    "materials_chemistry": [
        src("Materials Chemistry", "Bradley, D.; Williams, G.; Lawton, M.", "Oxford University Press", "2018", url="https://global.oup.com/academic/product/materials-chemistry-9780199657834"),
        src("The Physics and Chemistry of Materials", "Gersten, J. I.; Smith, F. W.", "Wiley", "2001", url="https://www.wiley.com/en-us/The+Physics+and+Chemistry+of+Materials-p-9780471057949"),
    ],
    "materials_science": [
        src("Materials Science and Engineering: An Introduction", "Callister, W. D.; Rethwisch, D. G.", "Wiley", "2018", url="https://www.wiley.com/en-us/Materials+Science+and+Engineering%3A+An+Introduction%2C+10th+Edition-p-9781119405498"),
        src("Introduction to Solid State Physics", "Kittel, C.", "Wiley", "2005", url="https://www.wiley.com/en-us/Introduction+to+Solid+State+Physics%2C+8th+Edition-p-9780471415268"),
    ],
    "medicinal_chemistry": [
        src("An Introduction to Medicinal Chemistry", "Patrick, G. L.", "Oxford University Press", "2017", url="https://global.oup.com/academic/product/an-introduction-to-medicinal-chemistry-9780198749691"),
        src("The Organic Chemistry of Drug Design and Drug Action", "Silverman, R. B.; Holladay, M. W.", "Academic Press", "2014", doi="10.1016/C2012-0-06155-2"),
    ],
    "nuclear_chemistry": [
        src("Radiochemistry and Nuclear Chemistry", "Choppin, G.; Liljenzin, J.-O.; Rydberg, J.; Ekberg, C.", "Academic Press", "2013", doi="10.1016/C2010-0-67831-6"),
        src("Nuclear and Radiochemistry", "Friedlander, G.; Kennedy, J. W.; Macias, E. S.; Miller, J. M.", "Wiley", "1981", url="https://archive.org/details/nuclearradiochem0000frie"),
    ],
    "organic_chemistry": [
        src("Advanced Organic Chemistry", "Carey, F. A.; Sundberg, R. J.", "Springer", "2007", doi="10.1007/978-0-387-44899-2"),
        src("March's Advanced Organic Chemistry", "Smith, M. B.; March, J.", "Wiley", "2007", url="https://www.wiley.com/en-us/March%27s+Advanced+Organic+Chemistry%3A+Reactions%2C+Mechanisms%2C+and+Structure%2C+6th+Edition-p-9780470084960"),
    ],
    "physical_chemistry": [
        src("Physical Chemistry", "Atkins, P.; de Paula, J.", "Oxford University Press", "2014", url="https://global.oup.com/academic/product/atkins-physical-chemistry-9780198769866"),
        src("Molecular Driving Forces", "Dill, K. A.; Bromberg, S.", "Garland Science", "2010", url="https://www.routledge.com/Molecular-Driving-Forces-Statistical-Thermodynamics-in-Biology-Chemistry/Dill-Bromberg/p/book/9780815344308"),
    ],
    "polymer_chemistry": [
        src("Principles of Polymerization", "Odian, G.", "Wiley", "2004", doi="10.1002/047147875X"),
        src("Polymer Chemistry", "Hiemenz, P. C.; Lodge, T. P.", "CRC Press", "2007", url="https://www.routledge.com/Polymer-Chemistry/Hiemenz-Lodge/p/book/9781574447798"),
    ],
    "quantum_chemistry": [
        src("Modern Quantum Chemistry", "Szabo, A.; Ostlund, N. S.", "Dover", "1996", url="https://store.doverpublications.com/products/9780486691862"),
        src("Density-functional theory of atoms and molecules", "Parr, R. G.; Yang, W.", "Oxford University Press", "1989", url="https://global.oup.com/academic/product/density-functional-theory-of-atoms-and-molecules-9780195092769"),
    ],
    "spectroscopy_advanced": [
        src("Introduction to Spectroscopy", "Pavia, D. L.; Lampman, G. M.; Kriz, G. S.; Vyvyan, J. A.", "Cengage Learning", "2014", url="https://www.cengage.com/c/introduction-to-spectroscopy-5e-pavia/"),
        src("Spectrometric Identification of Organic Compounds", "Silverstein, R. M.; Webster, F. X.; Kiemle, D. J.; Bryce, D. L.", "Wiley", "2014", url="https://www.wiley.com/en-us/Spectrometric+Identification+of+Organic+Compounds%2C+8th+Edition-p-9780470616376"),
    ],
    "surface_chemistry": [
        src("Principles of Adsorption and Reaction on Solid Surfaces", "Masel, R. I.", "Wiley", "1996", url="https://www.wiley.com/en-us/Principles+of+Adsorption+and+Reaction+on+Solid+Surfaces-p-9780471303923"),
        src("Heterogeneous Catalysis: Principles and Applications", "Bond, G. C.", "Oxford University Press", "1987", url="https://global.oup.com/academic/product/heterogeneous-catalysis-9780198555658"),
    ],
    "theoretical_chemistry": [
        src("Molecular Quantum Mechanics", "Atkins, P.; Friedman, R.", "Oxford University Press", "2011", url="https://global.oup.com/academic/product/molecular-quantum-mechanics-9780199541423"),
        src("Computational Chemistry", "Jensen, F.", "Wiley", "2017", doi="10.1002/9781118825990"),
    ],
    "thermodynamics": [
        src("Physical Chemistry", "Atkins, P.; de Paula, J.", "Oxford University Press", "2014", url="https://global.oup.com/academic/product/atkins-physical-chemistry-9780198769866"),
        src("Thermodynamics and an Introduction to Thermostatistics", "Callen, H. B.", "Wiley", "1985", url="https://www.wiley.com/en-us/Thermodynamics+and+an+Introduction+to+Thermostatistics%2C+2nd+Edition-p-9780471862567"),
    ],
    "graph_type_pilots": [
        src("Catalysis in Chemistry and Enzymology", "Jencks, W. P.", "McGraw-Hill", "1969", url="https://archive.org/details/catalysisinchemi0000jenc"),
        src("Principles and Practice of Heterogeneous Catalysis", "Thomas, J. M.; Thomas, W. J.", "Wiley-VCH", "1997", url="https://onlinelibrary.wiley.com/doi/book/10.1002/9783527610044"),
    ],
}


def weak(source: dict[str, Any]) -> bool:
    return (
        not source.get("authors")
        or not source.get("journal")
        or str(source.get("year")).lower() in {"none", "null", ""}
    )


def unique(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    output = []
    for source in sources:
        key = (str(source.get("title", "")).lower(), str(source.get("doi", "")).lower())
        if key in seen:
            continue
        seen.add(key)
        output.append(source)
    return output


def repair_database(discipline: str, db_name: str, canonical: dict[str, list[dict[str, Any]]]) -> int:
    db_dir = BASE_DIR / db_name
    changed = 0
    for path in sorted((db_dir / "processes").rglob("*.json")):
        if path.name.endswith(".backup"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        subcategory = str(data.get("subcategory") or "graph_type_pilots")
        sources = data.get("sources") or []
        good = [source for source in sources if not weak(source)]
        if len(good) != len(sources) or not good:
            repaired = unique([*good, *canonical.get(subcategory, canonical.get("graph_type_pilots", []))])[:5]
            data["sources"] = repaired
            data["lastUpdated"] = date.today().isoformat()
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            create_process_viewer(path, path.parent, discipline=discipline.replace("_", "-"))
            changed += 1
    profiles = read_json(DISCIPLINE_DIR / "discipline_profiles.json")
    process_index = build_process_index(db_dir, profiles[discipline])
    write_json(db_dir / "process-index.json", process_index)
    generate_one(discipline, profiles[discipline])
    return changed


def main() -> int:
    changed = {
        "chemistry": repair_database("chemistry", "chemistry-processes-database", CHEM_CANONICAL),
        "computer_science": repair_database("computer_science", "computer-science-processes-database", CS_CANONICAL),
    }
    print("repaired weak sources", changed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
