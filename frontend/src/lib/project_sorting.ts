// TODO: move sorting order to the backend
const PROJECT_ID_ORDER: number[] = [1, 2, 5, 6, 14, 9, 10, 11, 3, 4, 15, 7, 12, 8, 13, 16];

const projectIdToSortIndex = new Map<number, number>(
  PROJECT_ID_ORDER.map((id, index) => [id, index])
);

export function projectSortIndex(projectId: number): number {
  return projectIdToSortIndex.get(projectId) ?? PROJECT_ID_ORDER.length;
}
