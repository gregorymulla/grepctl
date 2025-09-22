#!/usr/bin/env python3
"""
Quick test of the grepctl Search API.
"""

from grepctl import SearchClient, search

def test_basic_api():
    """Test basic Search API functionality."""
    print("Testing grepctl Search API")
    print("=" * 50)

    # Test 1: Create client
    print("\n1. Creating SearchClient...")
    try:
        client = SearchClient()
        print("   ✅ Client created successfully")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # Test 2: Get stats
    print("\n2. Getting system statistics...")
    try:
        stats = client.get_stats()
        print(f"   ✅ Documents indexed: {stats['document_count']:,}")
        print(f"   ✅ Dataset: {stats['dataset_name']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Simple search
    print("\n3. Testing simple search...")
    try:
        results = client.search_simple("test", limit=2)
        print(f"   ✅ Found {len(results)} results")
        if results:
            print(f"   Preview: {results[0][:100]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Full search
    print("\n4. Testing full search with filters...")
    try:
        results = client.search(
            query="data",
            top_k=3,
            sources=["text", "markdown"],
        )
        print(f"   ✅ Found {len(results)} results")
        for i, r in enumerate(results, 1):
            print(f"   {i}. Score: {r['score']:.3f} | Source: {r['source']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 5: Quick search function
    print("\n5. Testing quick search function...")
    try:
        results = search("python", top_k=2)
        print(f"   ✅ Quick search found {len(results)} results")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 50)
    print("✅ All tests completed!")


if __name__ == "__main__":
    test_basic_api()