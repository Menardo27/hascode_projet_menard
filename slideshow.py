import sys
import os
from gurobipy import Model, GRB, quicksum

# ---- Lecture du fichier ----
def read_dataset(filename):
    with open(filename, "r") as f:
        lines = f.readlines()
    
    N = int(lines[0].strip())  # Nombre de photos
    photos = {}
    verticals = []

    for i in range(1, N + 1):
        data = lines[i].strip().split()
        orientation = data[0]
        tags = set(data[2:])
        photos[i - 1] = {"orientation": orientation, "tags": tags}
        if orientation == "V":
            verticals.append(i - 1)

    return photos, verticals

# ---- Création des diapositives possibles ----
def create_slides(photos, verticals):
    slides = []
    for pid, photo in photos.items():
        if photo["orientation"] == "H":
            slides.append((pid,))
    for i in range(0, len(verticals) - 1, 2):
        slides.append((verticals[i], verticals[i + 1]))
    return slides

# ---- Calcul du score de transition ----
def interest_factor(tags1, tags2):
    return min(len(tags1 & tags2), len(tags1 - tags2), len(tags2 - tags1))

# ---- Optimisation avec Gurobi ----
def optimize_slideshow(photos, slides):
    model = Model("Slideshow Optimization")
    model.setParam("OutputFlag", 0)  # Désactiver les logs pour une exécution plus rapide

    # Variables de sélection des diapositives
    x = model.addVars(slides, vtype=GRB.BINARY, name="x")

    # Variables de transition entre diapositives
    slide_tags = {s: set().union(*[photos[p]["tags"] for p in s]) for s in slides}
    slide_pairs = [(s1, s2) for s1 in slides for s2 in slides if s1 != s2]
    transition_scores = {(s1, s2): interest_factor(slide_tags[s1], slide_tags[s2]) for s1, s2 in slide_pairs}
    y = model.addVars(slide_pairs, vtype=GRB.BINARY, name="y")

    # Contraintes
    for pid in photos:
        model.addConstr(quicksum(x[s] for s in slides if pid in s) <= 1)
    for s1, s2 in slide_pairs:
        model.addConstr(y[s1, s2] <= x[s1])
        model.addConstr(y[s1, s2] <= x[s2])

    # Objectif : maximiser la somme des scores de transition
    model.setObjective(quicksum(transition_scores[s1, s2] * y[s1, s2] for s1, s2 in slide_pairs), GRB.MAXIMIZE)

    # Exécuter l'optimisation
    model.optimize()

    # Extraction de la solution
    return [s for s in slides if x[s].x > 0.5]

# ---- Calcul du score total ----
def compute_total_score(slideshow, photos):
    total_score = 0
    for i in range(len(slideshow) - 1):
        tags1 = set().union(*[photos[p]["tags"] for p in slideshow[i]])
        tags2 = set().union(*[photos[p]["tags"] for p in slideshow[i + 1]])
        total_score += interest_factor(tags1, tags2)
    return total_score

# ---- Sauvegarde de la solution ----
def write_solution(slideshow, output_file):
    with open(output_file, "w") as f:
        f.write(f"{len(slideshow)}\n")
        for slide in slideshow:
            f.write(" ".join(map(str, slide)) + "\n")

# ---- Exécution principale ----
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python slideshow.py [dataset1] [dataset2] ...")
        sys.exit(1)

    for dataset in sys.argv[1:]:
        if not os.path.exists(dataset):
            print(f"Erreur : fichier '{dataset}' introuvable.")
            continue

        print(f"\n📂 Traitement du dataset : {dataset}")

        photos, verticals = read_dataset(dataset)
        slides = create_slides(photos, verticals)
        solution = optimize_slideshow(photos, slides)
        score_total = compute_total_score(solution, photos)

        # Nom du fichier solution (ex: trivial.sol pour trivial.txt)
        output_file = dataset.replace(".txt", ".sol")
        write_solution(solution, output_file)

        print(f"✅ Solution optimale trouvée : {output_file}")
        print(f"🏆 Score total : {score_total}\n")
