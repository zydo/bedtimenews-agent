"""
Test tool for pure retrieval (no agentic processing).

This tool tests the raw vector database retrieval functionality using queries from test_data.py.
It bypasses the agentic RAG pipeline and directly calls the retriever for evaluation purposes.

Usage:
    # Test a single query directly
    docker compose exec agent python -m src.test_retriever --query "你的问题"
    docker compose exec agent python -m src.test_retriever -q "你的问题"

    # List available categories
    docker compose exec agent python -m src.test_retriever --list-categories

    # Test all queries
    docker compose exec agent python -m src.test_retriever

    # Test specific category
    docker compose exec agent python -m src.test_retriever --category education

    # Random sample of queries
    docker compose exec agent python -m src.test_retriever --random 10

    # Adjust retrieval parameters
    docker compose exec agent python -m src.test_retriever --match-count 10 --threshold 0.6

"""

import argparse
import random
import sys
from datetime import datetime
from typing import Any, Dict, List

from .models import RetrieveRequest
from .retriever import retriever
from .test_data import (
    ALL_QUERIES,
    CATEGORY_NAMES_CN,
    FLAT_QUERIES,
)


def main():
    parser = argparse.ArgumentParser(
        description="Test BedtimeNews retrieval without agentic processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    query_group = parser.add_mutually_exclusive_group()
    query_group.add_argument(
        "--query",
        "-q",
        type=str,
        help="Test a single query directly from command line",
    )
    query_group.add_argument(
        "--category",
        type=str,
        choices=list(ALL_QUERIES.keys()),
        help="Test queries from a specific category",
    )
    query_group.add_argument(
        "--random",
        type=int,
        metavar="N",
        help="Test N random queries",
    )

    parser.add_argument(
        "--match-count",
        type=int,
        default=5,
        help="Number of results to retrieve per query (default: 5)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Minimum similarity threshold (default: 0.5)",
    )

    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List all available query categories and exit",
    )

    args = parser.parse_args()

    if args.list_categories:
        print("\nAvailable query categories:")
        print("=" * 80)
        for category, queries in ALL_QUERIES.items():
            cn_name = CATEGORY_NAMES_CN.get(category, "")
            print(f"  {category:25s}: {len(queries):3d} queries  # {cn_name}")
        print("=" * 80)
        print(f"\nTotal: {len(ALL_QUERIES)} categories, {len(FLAT_QUERIES)} queries")
        return

    if args.query:
        queries = [{"category": "custom", "query": args.query}]
        print(f"\nTesting custom query: {args.query}")
    elif args.category:
        queries = [
            {"category": args.category, "query": q}
            for q in ALL_QUERIES.get(args.category, [])
        ]
        print(f"\nSelected category: {args.category} ({len(queries)} queries)")
    elif args.random:
        queries = random.sample(FLAT_QUERIES, min(args.random, len(FLAT_QUERIES)))
        print(f"\nSelected {len(queries)} random queries")
    else:
        queries = FLAT_QUERIES
        print(f"\nTesting all queries ({len(queries)} total)")

    if not queries:
        print("No queries to test", file=sys.stderr)
        sys.exit(1)

    try:
        _run_retrieval_test(
            queries=queries,
            match_count=args.match_count,
            match_threshold=args.threshold,
        )
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


def _format_summary(
    total_queries: int,
    results_stats: Dict[str, Any],
    elapsed_time: float,
) -> str:
    """Format overall summary statistics."""
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Total queries: {total_queries}")
    lines.append(f"Queries with results: {results_stats['queries_with_results']}")
    lines.append(f"Queries with no results: {results_stats['queries_without_results']}")
    lines.append(
        f"Average results per query: {results_stats['avg_results_per_query']:.2f}"
    )
    lines.append(f"Total documents retrieved: {results_stats['total_results']}")

    # Greeting stats
    if results_stats["greeting_tested"] > 0:
        lines.append("")
        lines.append("Greeting queries (should have no results):")
        lines.append(f"  Tested: {results_stats['greeting_tested']}")
        lines.append(f"  With results: {results_stats['greeting_with_results']}")
        lines.append(
            f"  Without results: {results_stats['greeting_tested'] - results_stats['greeting_with_results']}"
        )

    lines.append("")
    lines.append(f"Elapsed time: {elapsed_time:.2f}s")
    lines.append(f"Average time per query: {elapsed_time/total_queries:.2f}s")
    lines.append("=" * 80)
    return "\n".join(lines)


def _run_retrieval_test(
    queries: List[Dict[str, str]],
    match_count: int = 5,
    match_threshold: float = 0.5,
) -> None:
    """
    Run retrieval tests on a list of queries.

    Args:
        queries: List of query dictionaries with 'category' and 'query' keys
        match_count: Number of results to retrieve per query
        match_threshold: Minimum similarity threshold
        output_file: Optional file path to save results
    """
    print("\n" + "=" * 80)
    print("BedtimeNews Retriever Test")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total queries to test: {len(queries)}")
    print(f"Match count: {match_count}")
    print(f"Match threshold: {match_threshold}")
    print("=" * 80)
    print()

    results_stats = {
        "queries_with_results": 0,
        "queries_without_results": 0,
        "total_results": 0,
        "avg_results_per_query": 0.0,
        "greeting_tested": 0,
        "greeting_with_results": 0,
    }

    start_time = datetime.now()

    for i, query_info in enumerate(queries, 1):
        query = query_info["query"]
        category = query_info.get("category", "unknown")

        print(f"\n[{i}/{len(queries)}] Category: {category}")
        print(f"Testing: {query[:80]}...")

        try:
            # Create retrieval request
            request = RetrieveRequest(
                query=query,
                match_count=match_count,
                match_threshold=match_threshold,
                include_text=False,
                include_heading=True,
            )

            # Perform retrieval
            response = retriever.retrieve(request)
            results = response.results

            # Track category-specific stats
            is_greeting = category == "greeting"

            if is_greeting:
                results_stats["greeting_tested"] += 1
                if results:
                    results_stats["greeting_with_results"] += 1

            # Update statistics
            results_stats["total_results"] += len(results)
            if results:
                results_stats["queries_with_results"] += 1
                if is_greeting:
                    print(f"Found {len(results)} results (unexpected for {category})")
                else:
                    print(f"Found {len(results)} results")
            else:
                results_stats["queries_without_results"] += 1
                if is_greeting:
                    print("No results found (expected)")
                else:
                    print("No results found")

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)

    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()

    # Calculate average results per query
    results_stats["avg_results_per_query"] = (
        results_stats["total_results"] / len(queries) if queries else 0.0
    )

    # Format and print summary
    summary = _format_summary(len(queries), results_stats, elapsed_time)
    print(summary)


if __name__ == "__main__":
    main()
