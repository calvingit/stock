import { NextRequest, NextResponse } from 'next/server';

const FASTAPI_BASE = process.env.FASTAPI_BASE_URL || 'http://127.0.0.1:8899';
const CACHE_TTL = parseInt(process.env.FASTAPI_CACHE_TTL || '300', 10);
const TIMEOUT = parseInt(process.env.FASTAPI_TIMEOUT || '120000', 10);

// Simple in-memory LRU cache
const cache = new Map<string, { data: unknown; expiry: number }>();
const MAX_CACHE_SIZE = 1000;

function getCacheKey(path: string, params: URLSearchParams): string {
  return `${path}?${params.toString()}`;
}

function getFromCache(key: string): unknown | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() > entry.expiry) {
    cache.delete(key);
    return null;
  }
  return entry.data;
}

function setCache(key: string, data: unknown): void {
  if (cache.size >= MAX_CACHE_SIZE) {
    // Evict oldest entry
    const firstKey = cache.keys().next().value;
    if (firstKey) cache.delete(firstKey);
  }
  cache.set(key, { data, expiry: Date.now() + CACHE_TTL * 1000 });
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path?: string[] }> }
) {
  const { path: pathSegments } = await params;
  const path = pathSegments?.join('/') || '';
  const searchParams = request.nextUrl.searchParams;
  const cacheKey = getCacheKey(path, searchParams);

  // Check cache
  const cached = getFromCache(cacheKey);
  if (cached) {
    return NextResponse.json(cached, {
      headers: { 'X-Cache': 'HIT' },
    });
  }

  // Forward to FastAPI
  const url = `${FASTAPI_BASE}/api/${path}?${searchParams.toString()}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json' },
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      return NextResponse.json(
        { error: `FastAPI error: ${response.status} ${response.statusText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    setCache(cacheKey, data);

    return NextResponse.json(data, {
      headers: { 'X-Cache': 'MISS' },
    });
  } catch (error) {
    clearTimeout(timeoutId);
    const message = error instanceof Error ? error.message : 'Unknown error';
    return NextResponse.json(
      { error: `Proxy error: ${message}` },
      { status: 502 }
    );
  }
}
