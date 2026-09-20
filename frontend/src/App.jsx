import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import DatasetsPage from "./pages/DatasetsPage";
import UploadPage from "./pages/UploadPage";
import DatasetDetailPage from "./pages/DatasetDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DatasetsPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/datasets/:id" element={<DatasetDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
