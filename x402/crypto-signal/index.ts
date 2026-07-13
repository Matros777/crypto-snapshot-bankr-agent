export default async function handler(req: Request): Promise<Response> {
  try {
    const body = await req.json();
    
    const response = await fetch('http://localhost:10000/', {
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
