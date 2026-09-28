"""English content for the About page."""

from dash import html
import dash_bootstrap_components as dbc

from pages.about_image import FRAMEWORK_IMAGE_SRC


def get_layout():
    return html.Div(children=[
        dbc.Card(
            dbc.CardBody([
                html.H2(
                    "Reimagining Public Finance",
                    style={'marginBottom': '0em'},
                ),
                html.H5(
                    "Managing public resources for development outcomes",
                    style={'marginTop': '0em', 'fontWeight': 500},
                ),
                html.P([
                    html.B("Public finance is among governments' most important policy tools for promoting development. "),
                    "The ways in which governments raise and spend public resources have an impact on most aspects of a country's development, from economic growth to income distribution, and from service delivery to crisis response. Harnessing the powers to tax and spend in the pursuit of positive development outcomes is therefore one of the key challenges and responsibilities facing governments the world over. The international community, including the World Bank, has been supporting developing countries in improving their use of public finance tools to promote development outcomes for decades. In more recent years, economic crises, global pandemics, conflicts and increasing threats from climate change have made the job of managing public resources for development outcomes more challenging. Fiscal policy choices are constrained by growing levels of debt and economic uncertainty, and public financial management (PFM) systems are struggling to deliver on governments' fiscal policy objectives. "
                ]),
                html.P([
                    html.B("The 'Reimagining Public Finance' initiative aims to open a conversation on what a new approach focused on the role that the management of public resources can play in promoting better development outcomes could look like. "),
                    "It defines public finance as the combination of fiscal policies\u2014what governments intend to do through the raising and spending of public resources\u2014and PFM systems\u2014how governments manage these resources through different processes and mechanisms, including along the various stages of the budget cycle. It then explores the role that public finance can play in promoting development outcomes within each country's broader policy and institutional environment, and the reforms that might help strengthen it. The initiative seeks to gradually shift the way different stakeholders in the realm of public finance\u2014from governments to donors, and from oversight actors to citizens\u2014 think about managing public resources. It also seeks to propose ways to improve the support that the World Bank and other international actors provide to governments in this area."
                ]),
                html.Img(
                    width="90%",
                    style={'marginBottom': '1em'},
                    src=FRAMEWORK_IMAGE_SRC,
                ),
                html.P([
                    html.B("The proposed approach starts by focusing on the development outcomes that governments want to pursue, and builds its way back to how the effective functioning of public sector and fiscal institutions can support governments in achieving those outcomes. "),
                    "The first step in applying the framework is the selection of a specific development outcome (e.g. related to economic resilience, learning outcomes, or climate adaptation). The next step is to identify public sector results that contribute to those outcomes, and that are the result of the policies developed and delivered by public sector institutions. Only then can the discussion turn to how public finance can help. Fiscal policy decisions affect and are affected by public policies through their focus on three broad objectives: (a) overall fiscal sustainability; (b) resource mobilization and allocation; and (c) effectiveness and efficiency in the use of public resources. PFM systems support both the formulation and implementation of fiscal policies through various functions like budgeting, procurement, accounting, reporting and auditing. The two key questions that this approach focuses on are: (a) what is the specific role that public finance plays in shaping public sector results and achieving development outcomes, and how can this role be played most effectively? and (b) what are the key bottlenecks that need to be addressed to ensure that happens? Asking these questions strengthens the focus on the outcomes that PFM systems are supposed to help achieve, rather than on the systems themselves, and on the problems that need to be addressed, rather than on more abstract notions of what PFM systems should look like. Figure 1 below sketches out the key elements of this approach. "
                ]),
                html.P([
                    html.B("The proposed approach deliberately recognizes that public finance works within a broader policy and institutional environment. "),
                    "Fiscal policies are an (important) part of broader public policies that governments formulate and implement. And other public sector systems\u2014i.e. human resource management systems, intergovernmental relations and sector-specific systems\u2014play an important role alongside PFM systems in affecting delivery. Moreover, all of these systems operate within a broader context of formal and informal institutions that shape the incentives and guide the behavior of different actors. Recognizing the role of institutions means understanding that public finance is not just about policies and systems, but also about people\u2014what powers and interests they have, the incentives they face, and how these factors affect the decisions that they ultimately take. This in turn affects the feasibility of policies, the capability to deliver and ultimately the public sector results and development outcomes that countries are able to achieve. "
                ]),
                html.P([
                    html.B("Over the coming months, the World Bank will convene a collaborative process to discuss this proposed framework. "),
                    "The process will engage a range of stakeholders in helping to review and refine the proposed framework, better understand the linkages between public finance and development outcomes, identify the key bottlenecks that need to be addressed, and rethink support for public finance reforms. This will involve two phases: "
                ]),
                html.Ul([
                    html.Li([
                        "Firstly, ",
                        html.B("reviewing and reimagining public finance"),
                        ", which will include (a) global consultations culminating in a global conference on the Future of Public Finance in late 2024; (b) research to further elaborate, revise and test the proposed framework focusing on a set of specific development outcomes and country case studies; (c) a global report which traces the evolution of public finance in different contexts, identifies successes and areas for improvement, and makes the case for any needed changes to the existing approach to public finance reforms."
                    ]),
                    html.Li([
                        "Secondly, ",
                        html.B("putting into operation a renewed approach "),
                        "which may involve (d) preparing a set of supporting resources may include an online global public platform providing tools for practitioners, problem solving guides and training courses; and (e) applying the new approach in countries where opportunities present themselves."
                    ]),
                ]),
                html.P([
                    "For further details and to get involved please contact: reimaginingPFM@worldbank.org"
                ]),
            ], style={"color": "#666"})
            , style={"backgroundImage": "linear-gradient(125deg,rgba(255,255,255,.8),rgba(255,255,255,1) 70%)"})
    ])
