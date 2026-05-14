"""French content for the About page."""

from dash import html
import dash_bootstrap_components as dbc

from pages.about_image import FRAMEWORK_IMAGE_SRC


def get_layout():
    return html.Div(children=[
        dbc.Card(
            dbc.CardBody([
                html.H2(
                    "Repenser les finances publiques",
                    style={'marginBottom': '0em'},
                ),
                html.H5(
                    "Gestion des ressources publiques pour les résultats de développement",
                    style={'marginTop': '0em', 'fontWeight': 500},
                ),
                html.P([
                    html.B("Les finances publiques comptent parmi les outils politiques les plus importants des gouvernements pour promouvoir le développement. "),
                    "La manière dont les gouvernements mobilisent et dépensent les ressources publiques a un impact sur la plupart des aspects du développement d'un pays, de la croissance économique à la distribution des revenus, et de la prestation de services à la réponse aux crises. Exploiter les pouvoirs de taxation et de dépense dans la poursuite de résultats de développement positifs est donc l'un des principaux défis et responsabilités auxquels sont confrontés les gouvernements du monde entier. La communauté internationale, y compris la Banque mondiale, soutient les pays en développement dans l'amélioration de leur utilisation des outils de finances publiques pour promouvoir les résultats de développement depuis des décennies. Plus récemment, les crises économiques, les pandémies mondiales, les conflits et les menaces croissantes du changement climatique ont rendu la gestion des ressources publiques pour les résultats de développement plus difficile. Les choix de politique budgétaire sont contraints par des niveaux d'endettement croissants et l'incertitude économique, et les systèmes de gestion des finances publiques (GFP) peinent à atteindre les objectifs de politique budgétaire des gouvernements. "
                ]),
                html.P([
                    html.B("L'initiative 'Repenser les finances publiques' vise à ouvrir une conversation sur ce à quoi pourrait ressembler une nouvelle approche centrée sur le rôle que la gestion des ressources publiques peut jouer dans la promotion de meilleurs résultats de développement. "),
                    "Elle définit les finances publiques comme la combinaison des politiques budgétaires — ce que les gouvernements entendent faire par la mobilisation et la dépense des ressources publiques — et des systèmes de GFP — la manière dont les gouvernements gèrent ces ressources à travers différents processus et mécanismes, y compris aux différentes étapes du cycle budgétaire. Elle explore ensuite le rôle que les finances publiques peuvent jouer dans la promotion des résultats de développement dans l'environnement politique et institutionnel plus large de chaque pays, et les réformes qui pourraient contribuer à le renforcer. L'initiative cherche à modifier progressivement la manière dont les différentes parties prenantes dans le domaine des finances publiques — des gouvernements aux donateurs, et des acteurs de contrôle aux citoyens — pensent la gestion des ressources publiques. Elle cherche également à proposer des moyens d'améliorer le soutien que la Banque mondiale et d'autres acteurs internationaux apportent aux gouvernements dans ce domaine."
                ]),
                html.Img(
                    width="90%",
                    style={'marginBottom': '1em'},
                    src=FRAMEWORK_IMAGE_SRC,
                ),
                html.P([
                    html.B("L'approche proposée commence par se concentrer sur les résultats de développement que les gouvernements souhaitent poursuivre, et remonte vers la manière dont le fonctionnement efficace des institutions du secteur public et budgétaires peut aider les gouvernements à atteindre ces résultats. "),
                    "La première étape dans l'application du cadre est la sélection d'un résultat de développement spécifique (par exemple lié à la résilience économique, aux résultats d'apprentissage ou à l'adaptation climatique). L'étape suivante consiste à identifier les résultats du secteur public qui contribuent à ces résultats, et qui sont le fruit des politiques développées et mises en oeuvre par les institutions du secteur public. Ce n'est qu'ensuite que la discussion peut porter sur la manière dont les finances publiques peuvent aider. Les décisions de politique budgétaire affectent et sont affectées par les politiques publiques à travers leur concentration sur trois grands objectifs : (a) la viabilité budgétaire globale ; (b) la mobilisation et l'allocation des ressources ; et (c) l'efficacité et l'efficience dans l'utilisation des ressources publiques. Les systèmes de GFP soutiennent à la fois la formulation et la mise en oeuvre des politiques budgétaires à travers diverses fonctions comme la budgétisation, les marchés publics, la comptabilité, les rapports et l'audit. Les deux questions clés sur lesquelles cette approche se concentre sont : (a) quel est le rôle spécifique que jouent les finances publiques dans la formation des résultats du secteur public et la réalisation des résultats de développement, et comment ce rôle peut-il être joué le plus efficacement ? et (b) quels sont les principaux goulets d'étranglement qui doivent être traités pour garantir que cela se produise ? Poser ces questions renforce l'accent sur les résultats que les systèmes de GFP sont censés aider à atteindre, plutôt que sur les systèmes eux-mêmes, et sur les problèmes qui doivent être résolus, plutôt que sur des notions plus abstraites de ce à quoi les systèmes de GFP devraient ressembler. La figure 1 ci-dessous esquisse les éléments clés de cette approche. "
                ]),
                html.P([
                    html.B("L'approche proposée reconnaît délibérément que les finances publiques fonctionnent dans un environnement politique et institutionnel plus large. "),
                    "Les politiques budgétaires sont une partie (importante) des politiques publiques plus larges que les gouvernements formulent et mettent en oeuvre. Et d'autres systèmes du secteur public — c'est-à-dire les systèmes de gestion des ressources humaines, les relations intergouvernementales et les systèmes sectoriels — jouent un rôle important aux côtés des systèmes de GFP dans la prestation. De plus, tous ces systèmes fonctionnent dans un contexte plus large d'institutions formelles et informelles qui façonnent les incitations et guident le comportement des différents acteurs. Reconnaître le rôle des institutions signifie comprendre que les finances publiques ne concernent pas seulement les politiques et les systèmes, mais aussi les personnes — quels pouvoirs et intérêts elles ont, les incitations auxquelles elles font face, et comment ces facteurs affectent les décisions qu'elles prennent finalement. Cela affecte à son tour la faisabilité des politiques, la capacité à produire et finalement les résultats du secteur public et les résultats de développement que les pays sont en mesure d'atteindre. "
                ]),
                html.P([
                    html.B("Au cours des prochains mois, la Banque mondiale organisera un processus collaboratif pour discuter de ce cadre proposé. "),
                    "Le processus engagera un éventail de parties prenantes pour aider à examiner et affiner le cadre proposé, mieux comprendre les liens entre les finances publiques et les résultats de développement, identifier les principaux goulets d'étranglement à traiter, et repenser le soutien aux réformes des finances publiques. Cela impliquera deux phases : "
                ]),
                html.Ul([
                    html.Li([
                        "Premièrement, ",
                        html.B("examiner et repenser les finances publiques"),
                        ", ce qui comprendra (a) des consultations mondiales culminant en une conférence mondiale sur l'avenir des finances publiques fin 2024 ; (b) des recherches pour élaborer, réviser et tester le cadre proposé en se concentrant sur un ensemble de résultats de développement spécifiques et d'études de cas nationales ; (c) un rapport mondial qui retrace l'évolution des finances publiques dans différents contextes, identifie les succès et les domaines d'amélioration, et plaide pour tout changement nécessaire de l'approche existante des réformes des finances publiques."
                    ]),
                    html.Li([
                        "Deuxièmement, ",
                        html.B("mettre en oeuvre une approche renouvelée "),
                        "qui pourra impliquer (d) la préparation d'un ensemble de ressources de soutien pouvant inclure une plateforme publique mondiale en ligne fournissant des outils pour les praticiens, des guides de résolution de problèmes et des cours de formation ; et (e) l'application de la nouvelle approche dans les pays où des opportunités se présentent."
                    ]),
                ]),
                html.P([
                    "Pour plus de détails et pour vous impliquer, veuillez contacter : reimaginingPFM@worldbank.org"
                ]),
            ], style={"color": "#666"})
            , style={"backgroundImage": "linear-gradient(125deg,rgba(255,255,255,.8),rgba(255,255,255,1) 70%)"})
    ])
