import sys
import os
from gurobipy import Model, GRB, quicksum
from itertools import combinations

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
    
    # Ajouter les photos horizontales comme slides individuels
    for pid, photo in photos.items():
        if photo["orientation"] == "H":
            slides.append((pid,))

    # Générer toutes les combinaisons possibles de paires de photos verticales
    vertical_pairs = list(combinations(verticals, 2))
    
    # Ajouter toutes les paires possibles à la liste des slides
    slides.extend(vertical_pairs)

    return slides

# ---- Calcul du score de transition ----
def interest_factor(tags1, tags2):
    return min(len(tags1 & tags2), len(tags1 - tags2), len(tags2 - tags1))

# ---- Optimisation avec Gurobi ----
def optimize_slideshow(photos, slides):
    model = Model("Slideshow Optimization")

    print("\n🚀 Lancement de l'optimisation Gurobi...")

    # Séparer les slides horizontaux et verticaux
    horizontal_slides = [s for s in slides if len(s) == 1]
    vertical_slides = [s for s in slides if len(s) == 2]

    # Variables de sélection des diapositives
    x = model.addVars(slides, vtype=GRB.BINARY, name="x")

    # Variables de transition entre diapositives
    slide_tags = {s: set().union(*[photos[p]["tags"] for p in s]) for s in slides}
    slide_pairs = [(s1, s2) for s1 in slides for s2 in slides if s1 != s2]
    transition_scores = {(s1, s2): interest_factor(slide_tags[s1], slide_tags[s2]) for s1, s2 in slide_pairs}
    y = model.addVars(slide_pairs, vtype=GRB.BINARY, name="y")

    # Contrainte : une photo ne peut apparaître qu'une seule fois
    for pid in photos:
        model.addConstr(quicksum(x[s] for s in slides if pid in s) <= 1)

    # Contrainte : une transition ne peut exister que si les deux diapositives sont sélectionnées
    for s1, s2 in slide_pairs:
        model.addConstr(y[s1, s2] <= x[s1])
        model.addConstr(y[s1, s2] <= x[s2])

    # Variables pour compter les types de slides sélectionnés
    h_count = quicksum(x[s] for s in horizontal_slides)
    v_count = quicksum(x[s] for s in vertical_slides)

    # Assurer que le diaporama contient au moins un slide horizontal et un slide vertical si possible
    if len(horizontal_slides) > 0:
        model.addConstr(h_count >= 1, "At least one horizontal slide")
    if len(vertical_slides) > 0:
        model.addConstr(v_count >= 1, "At least one vertical slide")

    # Objectif : maximiser la somme des scores de transition
    model.setObjective(quicksum(transition_scores[s1, s2] * y[s1, s2] for s1, s2 in slide_pairs), GRB.MAXIMIZE)

    # Exécuter l'optimisation
    model.optimize()

    # Récupérer les slides sélectionnés
    selected_slides = [s for s in slides if x[s].x > 0.5]

    # Trouver le meilleur ordre pour maximiser le score
    best_order = order_slides(selected_slides, transition_scores)

    return best_order

# ---- Ordonner les slides pour maximiser le score ----
def order_slides(slides, transition_scores):
    """ Trouve l'ordre des slides maximisant le score des transitions """
    ordered_slides = []
    remaining_slides = set(slides)

    # Commencer avec un slide aléatoire
    current_slide = remaining_slides.pop()
    ordered_slides.append(current_slide)

    while remaining_slides:
        # Trouver le slide qui donne la meilleure transition avec le dernier ajouté
        next_slide = max(remaining_slides, key=lambda s: transition_scores.get((current_slide, s), 0))
        ordered_slides.append(next_slide)
        remaining_slides.remove(next_slide)
        current_slide = next_slide

    return ordered_slides

# ---- Calcul du score total ----
def compute_total_score(slideshow, photos):
    total_score = 0
    for i in range(len(slideshow) - 1):
        tags1 = set().union(*[photos[p]["tags"] for p in slideshow[i]])
        tags2 = set().union(*[photos[p]["tags"] for p in slideshow[i + 1]])
        total_score += interest_factor(tags1, tags2)
    return total_score

# ---- Sauvegarde de la solution ----
def write_solution(slideshow):
    with open("slideshow.sol", "w") as f:
        f.write(f"{len(slideshow)}\n")
        for slide in slideshow:
            f.write(" ".join(map(str, slide)) + "\n")

# ---- Exécution principale ----
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python slideshow.py [dataset]")
        sys.exit(1)

    dataset = sys.argv[1]  # On prend uniquement le premier fichier donné
    if not os.path.exists(dataset):
        print(f"❌ Erreur : fichier '{dataset}' introuvable.")
        sys.exit(1)

    print(f"\n📂 Traitement du dataset : {dataset}")

    photos, verticals = read_dataset(dataset)
    slides = create_slides(photos, verticals)
    solution = optimize_slideshow(photos, slides)
    score_total = compute_total_score(solution, photos)

    write_solution(solution)

    print(f"✅ Solution optimale trouvée et sauvegardée dans 'slideshow.sol'")
    print(f"🏆 Score total : {score_total}\n")
