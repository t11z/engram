export interface ExtractSuccess {
  ok: true;
  title: string;
  markdown: string;
}

export interface ExtractFailure {
  ok: false;
  error: string;
}

export type ExtractResponse = ExtractSuccess | ExtractFailure;
