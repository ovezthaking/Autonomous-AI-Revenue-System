export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const parse = async <T>(res: Response): Promise<T> => {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
};
