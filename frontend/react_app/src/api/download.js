import { apiClient } from "./client";

export async function downloadAuthenticatedFile(endpoint, filename) {
  const response = await apiClient.get(endpoint, {
    responseType: "blob",
  });

  const downloadUrl = URL.createObjectURL(response.data);
  const downloadLink = document.createElement("a");

  downloadLink.href = downloadUrl;
  downloadLink.download = filename;
  document.body.appendChild(downloadLink);
  downloadLink.click();
  downloadLink.remove();
  URL.revokeObjectURL(downloadUrl);
}
