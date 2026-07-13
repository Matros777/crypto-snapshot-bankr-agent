export default async function handler(req: Request): Promise<Response> {
  try {
    const body = await req.json();
    
    // ⚠️ МЕНЯЕМ URL НА RENDER (КОГДА ЗАДЕПЛОИШЬ)
    const response = await fetch('https://crypto-snapshot-bankr-agent.onrender.com/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-payment': req.headers.get('x-payment') || ''
      },
      body: JSON.stringify(body)
    });

    const data = await response.json();

    return Response.json(data, {
      status: response.status
    });

  } catch (error) {
    return Response.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
