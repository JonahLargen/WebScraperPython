import logging

import matplotlib

matplotlib.use("Agg") # no display on a server, so render straight to a file

import matplotlib.pyplot as plt # noqa: E402
import networkx as nx # noqa: E402

from crawl import normalize_url # noqa: E402

MAX_LABELLED_NODES = 60

logger = logging.getLogger(__name__)


def write_graph_report(page_data, filename="report.png"):
    if not page_data:
        logger.warning("no pages to graph, skipping %s", filename)
        return None

    graph = build_graph(page_data)
    positions = nx.spring_layout(graph, seed=42, k=0.6, iterations=80)

    in_degrees = dict(graph.in_degree())
    node_sizes = [120 + 220 * in_degrees[node] for node in graph]
    node_colors = [graph.nodes[node]["external_link_count"] for node in graph]

    size = figure_size(graph.number_of_nodes())
    figure, axes = plt.subplots(figsize=(size, size))

    nx.draw_networkx_edges(
        graph,
        positions,
        ax=axes,
        edge_color="#b0bec5",
        width=0.6,
        alpha=0.6,
        arrowsize=7,
        node_size=node_sizes,
    )
    nodes = nx.draw_networkx_nodes(
        graph,
        positions,
        ax=axes,
        node_size=node_sizes,
        node_color=node_colors,
        cmap=plt.cm.viridis,
        linewidths=0.5,
        edgecolors="#37474f",
    )

    if graph.number_of_nodes() <= MAX_LABELLED_NODES:
        labels = {node: graph.nodes[node]["label"] for node in graph}
        nx.draw_networkx_labels(graph, positions, labels, ax=axes, font_size=7)

    figure.colorbar(nodes, ax=axes, shrink=0.6, label="external links on page")
    axes.set_title(
        f"{graph.number_of_nodes()} pages, {graph.number_of_edges()} internal links"
        "\n(node size = inbound links)"
    )
    axes.axis("off")
    figure.tight_layout()
    figure.savefig(filename, dpi=150)
    plt.close(figure)

    return filename


def build_graph(page_data):
    graph = nx.DiGraph()

    for normalized_url, page in page_data.items():
        graph.add_node(
            normalized_url,
            label=short_label(normalized_url),
            external_link_count=page["external_link_count"],
        )

    for normalized_url, page in page_data.items():
        for link in page["internal_links"]:
            target = safe_normalize(link)
            if target is None or target == normalized_url:
                continue # self links add noise, not information
            if target in page_data: # a link we never crawled has no node to point at
                graph.add_edge(normalized_url, target)

    return graph


def short_label(normalized_url, limit=28):
    _, _, path = normalized_url.partition("/")
    label = path.rsplit("/", 1)[-1] or path or "/"
    if len(label) <= limit:
        return label

    return label[: limit - 1] + "…"


def safe_normalize(url):
    try:
        return normalize_url(url)
    except (TypeError, ValueError):
        return None


def figure_size(node_count):
    return min(24, max(8, node_count ** 0.5 * 1.6))
