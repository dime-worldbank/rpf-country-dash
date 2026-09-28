"""Brazilian Portuguese content for the About page."""

from dash import html
import dash_bootstrap_components as dbc

from pages.about_image import FRAMEWORK_IMAGE_SRC


def get_layout():
    return html.Div(children=[
        dbc.Card(
            dbc.CardBody([
                html.H2(
                    "Repensando as Finanças Públicas",
                    style={'marginBottom': '0em'},
                ),
                html.H5(
                    "Gestão dos recursos públicos para resultados de desenvolvimento",
                    style={'marginTop': '0em', 'fontWeight': 500},
                ),
                html.P([
                    html.B("As finanças públicas estão entre as ferramentas de política mais importantes dos governos para promover o desenvolvimento. "),
                    "A forma como os governos arrecadam e gastam recursos públicos afeta a maior parte dos aspectos do desenvolvimento de um país, do crescimento econômico à distribuição de renda, e da prestação de serviços à resposta a crises. Usar o poder de tributar e gastar em busca de resultados positivos de desenvolvimento é, portanto, um dos principais desafios e responsabilidades dos governos em todo o mundo. A comunidade internacional, incluindo o Banco Mundial, apoia há décadas os países em desenvolvimento no aprimoramento do uso das ferramentas de finanças públicas para promover resultados de desenvolvimento. Mais recentemente, crises econômicas, pandemias globais, conflitos e ameaças crescentes das mudanças climáticas tornaram mais difícil a gestão dos recursos públicos para resultados de desenvolvimento. As escolhas de política fiscal são limitadas por níveis crescentes de dívida e incerteza econômica, e os sistemas de gestão das finanças públicas (GFP) enfrentam dificuldades para cumprir os objetivos de política fiscal dos governos. "
                ]),
                html.P([
                    html.B("A iniciativa 'Repensando as Finanças Públicas' busca abrir uma conversa sobre como poderia ser uma nova abordagem centrada no papel que a gestão dos recursos públicos pode desempenhar na promoção de melhores resultados de desenvolvimento. "),
                    "Ela define finanças públicas como a combinação de políticas fiscais - o que os governos pretendem fazer ao arrecadar e gastar recursos públicos - e sistemas de GFP - como os governos gerenciam esses recursos por meio de diferentes processos e mecanismos, inclusive ao longo das várias etapas do ciclo orçamentário. Em seguida, explora o papel que as finanças públicas podem desempenhar na promoção de resultados de desenvolvimento dentro do ambiente político e institucional mais amplo de cada país, e as reformas que poderiam fortalecê-lo. A iniciativa busca mudar gradualmente a forma como diferentes atores no campo das finanças públicas - de governos a doadores, e de órgãos de controle a cidadãos - pensam sobre a gestão dos recursos públicos. Também procura propor formas de melhorar o apoio que o Banco Mundial e outros atores internacionais oferecem aos governos nessa área."
                ]),
                html.Img(
                    width="90%",
                    style={'marginBottom': '1em'},
                    src=FRAMEWORK_IMAGE_SRC,
                ),
                html.P([
                    html.B("A abordagem proposta começa pelos resultados de desenvolvimento que os governos desejam alcançar e retrocede até a forma como o funcionamento efetivo das instituições do setor público e fiscais pode apoiar esses governos na obtenção desses resultados. "),
                    "O primeiro passo na aplicação do marco é selecionar um resultado específico de desenvolvimento, por exemplo relacionado à resiliência econômica, resultados de aprendizagem ou adaptação climática. O passo seguinte é identificar resultados do setor público que contribuem para esses objetivos e que decorrem de políticas desenvolvidas e entregues por instituições públicas. Somente então a discussão passa a tratar de como as finanças públicas podem ajudar. Decisões de política fiscal afetam e são afetadas pelas políticas públicas por meio de três objetivos amplos: (a) sustentabilidade fiscal geral; (b) mobilização e alocação de recursos; e (c) efetividade e eficiência no uso dos recursos públicos. Os sistemas de GFP apoiam tanto a formulação quanto a implementação das políticas fiscais por meio de funções como orçamentação, compras públicas, contabilidade, relatórios e auditoria. As duas perguntas centrais dessa abordagem são: (a) qual é o papel específico das finanças públicas na formação de resultados do setor público e na realização de resultados de desenvolvimento, e como esse papel pode ser desempenhado de forma mais efetiva? e (b) quais são os principais gargalos que precisam ser enfrentados para que isso aconteça? Fazer essas perguntas reforça o foco nos resultados que os sistemas de GFP devem ajudar a alcançar, e não nos sistemas em si, e nos problemas que precisam ser resolvidos, em vez de em ideias abstratas sobre como esses sistemas deveriam ser. A Figura 1 abaixo resume os principais elementos dessa abordagem. "
                ]),
                html.P([
                    html.B("A abordagem proposta reconhece deliberadamente que as finanças públicas operam em um ambiente político e institucional mais amplo. "),
                    "As políticas fiscais são uma parte importante das políticas públicas mais amplas que os governos formulam e implementam. Outros sistemas do setor público - como gestão de recursos humanos, relações intergovernamentais e sistemas setoriais - também desempenham papel importante ao lado dos sistemas de GFP na prestação de serviços. Além disso, todos esses sistemas funcionam em um contexto mais amplo de instituições formais e informais que moldam incentivos e orientam o comportamento de diferentes atores. Reconhecer o papel das instituições significa entender que finanças públicas não dizem respeito apenas a políticas e sistemas, mas também a pessoas - quais poderes e interesses elas têm, quais incentivos enfrentam e como esses fatores afetam as decisões que acabam tomando. Isso, por sua vez, afeta a viabilidade das políticas, a capacidade de entrega e, em última instância, os resultados do setor público e de desenvolvimento que os países conseguem alcançar. "
                ]),
                html.P([
                    html.B("Nos próximos meses, o Banco Mundial convocará um processo colaborativo para discutir esse marco proposto. "),
                    "O processo envolverá uma variedade de partes interessadas para ajudar a revisar e aperfeiçoar o marco proposto, compreender melhor os vínculos entre finanças públicas e resultados de desenvolvimento, identificar os principais gargalos a enfrentar e repensar o apoio às reformas de finanças públicas. Isso envolverá duas fases: "
                ]),
                html.Ul([
                    html.Li([
                        "Primeiro, ",
                        html.B("revisar e repensar as finanças públicas"),
                        ", incluindo (a) consultas globais culminando em uma conferência global sobre o Futuro das Finanças Públicas no fim de 2024; (b) pesquisas para elaborar, revisar e testar o marco proposto com foco em resultados específicos de desenvolvimento e estudos de caso de países; e (c) um relatório global que acompanha a evolução das finanças públicas em diferentes contextos, identifica sucessos e áreas de melhoria e apresenta argumentos para eventuais mudanças necessárias na abordagem existente das reformas de finanças públicas."
                    ]),
                    html.Li([
                        "Segundo, ",
                        html.B("colocar em operação uma abordagem renovada "),
                        "que poderá envolver (d) a preparação de um conjunto de recursos de apoio, incluindo uma plataforma pública global on-line com ferramentas para profissionais, guias de resolução de problemas e cursos de formação; e (e) a aplicação da nova abordagem em países onde surgirem oportunidades."
                    ]),
                ]),
                html.P([
                    "Para mais detalhes e para se envolver, entre em contato: reimaginingPFM@worldbank.org"
                ]),
            ], style={"color": "#666"})
            , style={"backgroundImage": "linear-gradient(125deg,rgba(255,255,255,.8),rgba(255,255,255,1) 70%)"})
    ])
