package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

const (
	apiKey        = "sk-96b39dfd062849249d7e3d1989382bd2" // Replace with your actual API key
	apiURL        = "https://chat.lilbro.cloud/api/v1/"
	knowledgeName = "OpenWebUI Documentation"
	knowledgeDesc = "Documentation for Open WebUI"
	docsUrl       = "https://github.com/open-webui/docs/archive/refs/heads/main.zip"
)

// Global variable for the zip URL, settable via command-line flag
var docsZipURL string

type APIResponse struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	Description string   `json:"description"`
	FileIDs     []string `json:"file_ids"`
	Message     string   `json:"message"` // For error responses
}

func apiRequest(method, endpoint string, data []byte) ([]byte, int, error) {
	req, err := http.NewRequest(method, apiURL+endpoint, bytes.NewBuffer(data))
	if err != nil {
		return nil, 0, err
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, 0, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, 0, err
	}
	return body, resp.StatusCode, nil
}

func copyMarkdownFiles(docsDir, zipURL string) (string, error) {
	tempDir, err := os.MkdirTemp("", "openwebui-docs")
	if err != nil {
		return "", fmt.Errorf("creating temp dir: %w", err)
	}
	defer os.RemoveAll(tempDir)

	zipPath := filepath.Join(tempDir, "docs.zip")
	err = downloadFile(zipPath, zipURL)
	if err != nil {
		return "", fmt.Errorf("downloading docs: %w", err)
	}

	r, err := zip.OpenReader(zipPath)
	if err != nil {
		return "", fmt.Errorf("opening zip: %w", err)
	}
	defer r.Close()

	extractedDir := ""
	for i, f := range r.File {
		if i == 0 {
			extractedDir = filepath.Join(tempDir, f.Name)
			continue
		}

		fpath := filepath.Join(tempDir, f.Name)
		if f.FileInfo().IsDir() {
			if err := os.MkdirAll(fpath, os.ModePerm); err != nil {
				return "", fmt.Errorf("creating directory %s: %w", fpath, err)
			}
			continue
		}

		if !strings.HasSuffix(fpath, ".md") && !strings.HasSuffix(fpath, ".mdx") {
			continue
		}

		outFile, err := os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())
		if err != nil {
			return "", fmt.Errorf("creating file %s: %w", fpath, err)
		}

		rc, err := f.Open()
		if err != nil {
			outFile.Close()
			return "", fmt.Errorf("opening file in zip: %w", err)
		}

		_, err = io.Copy(outFile, rc)
		rc.Close()
		outFile.Close()
		if err != nil {
			return "", fmt.Errorf("copying file content: %w", err)
		}
	}

	contentDir := filepath.Join(docsDir, "docs_content")
	if err := os.MkdirAll(contentDir, os.ModePerm); err != nil {
		return "", fmt.Errorf("creating docs_content dir: %w", err)
	}

	err = filepath.WalkDir(extractedDir, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}

		if !d.IsDir() && (strings.HasSuffix(path, ".md") || strings.HasSuffix(path, ".mdx")) {
			relPath, err := filepath.Rel(extractedDir, path)
			if err != nil {
				return err
			}
			destPath := filepath.Join(contentDir, relPath)
			if err := os.MkdirAll(filepath.Dir(destPath), os.ModePerm); err != nil {
				return err
			}

			if err := copyFile(path, destPath); err != nil {
				return err
			}
		}
		return nil
	})

	if err != nil {
		return "", fmt.Errorf("walking extracted directory: %w", err)
	}

	return contentDir, nil
}

func copyFile(src, dest string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dest)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	if err != nil {
		return err
	}
	return nil
}

func downloadFile(filepath, url string) error {
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	out, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	return err
}

func resetKnowledge(collectionID string) error {
	_, statusCode, err := apiRequest("POST", fmt.Sprintf("knowledge/%s/reset", collectionID), nil)
	if err != nil {
		return err
	}
	if statusCode != http.StatusOK {
		return fmt.Errorf("reset knowledge failed, status code: %d", statusCode)
	}
	return nil
}

func initKnowledge() (string, error) {
	collectionsData, _, err := apiRequest("GET", "knowledge/list", nil)
	if err != nil {
		return "", err
	}

	var collections []APIResponse
	err = json.Unmarshal(collectionsData, &collections)
	if err != nil {
		return "", fmt.Errorf("unmarshaling collections: %w", err)
	}

	for _, collection := range collections {
		if collection.Name == knowledgeName {
			if err := resetKnowledge(collection.ID); err != nil {
				return "", err
			}
			return collection.ID, nil
		}
	}

	data := map[string]interface{}{
		"name":        knowledgeName,
		"description": knowledgeDesc,
		"data":        map[string]interface{}{"file_ids": []string{}},
	}
	jsonData, err := json.Marshal(data)
	if err != nil {
		return "", fmt.Errorf("marshaling create knowledge data: %w", err)
	}

	responseData, statusCode, err := apiRequest("POST", "knowledge/create", jsonData)
	if err != nil {
		return "", err
	}

	if statusCode != http.StatusOK {
		return "", fmt.Errorf("create knowledge failed, status code: %d", statusCode)
	}

	var response APIResponse
	err = json.Unmarshal(responseData, &response)
	if err != nil {
		return "", fmt.Errorf("unmarshaling create knowledge response: %w", err)
	}

	return response.ID, nil
}

func uploadFile(filepath string) (string, error) {
	file, err := os.Open(filepath)
	if err != nil {
		return "", err
	}
	defer file.Close()

	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, err := writer.CreateFormFile("file", filepath)
	if err != nil {
		return "", err
	}
	_, err = io.Copy(part, file)
	if err != nil {
		return "", err
	}
	writer.Close()

	req, err := http.NewRequest("POST", apiURL+"files/", body)
	if err != nil {
		return "", err
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("upload failed, status code: %d", resp.StatusCode)
	}

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	var response APIResponse
	err = json.Unmarshal(respBody, &response)
	if err != nil {
		return "", fmt.Errorf("unmarshaling upload response: %w", err)
	}

	return response.ID, nil
}

func addFileToKnowledge(knowledgeID, fileID string) error {
	if checkFileInKnowledge(knowledgeID, fileID) {
		return nil // File already exists
	}

	data := map[string]string{"file_id": fileID}
	jsonData, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("marshaling add file data: %w", err)
	}

	_, statusCode, err := apiRequest("POST", fmt.Sprintf("knowledge/%s/file/add", knowledgeID), jsonData)
	if err != nil {
		return err
	}
	if statusCode != http.StatusOK {
		return fmt.Errorf("add file failed, status code: %d", statusCode)
	}

	return nil
}

func checkFileInKnowledge(knowledgeID, fileID string) bool {
	responseData, _, err := apiRequest("GET", fmt.Sprintf("knowledge/%s", knowledgeID), nil)
	if err != nil {
		log.Printf("Error checking file in knowledge: %v", err)
		return false // Handle error appropriately
	}

	var response APIResponse
	err = json.Unmarshal(responseData, &response)
	if err != nil {
		log.Printf("Error unmarshaling response: %v", err)
		return false // Handle error appropriately
	}

	for _, existingFileID := range response.FileIDs {
		if existingFileID == fileID {
			return true
		}
	}
	return false
}

func extractStringField(response []byte, field string) (string, error) {
	re := regexp.MustCompile(fmt.Sprintf(`"%s":"((?:[^"\\]|\\.)*)"`, field))
	match := re.FindSubmatch(response)
	if len(match) > 1 {

		unescaped, err := unescapeString(string(match[1]))
		if err != nil {
			return "", fmt.Errorf("unescaping string: %w", err)
		}
		return unescaped, nil
	}
	return "", fmt.Errorf("field %s not found", field)
}

func extractArrayField(response []byte, field string) ([]string, error) {
	re := regexp.MustCompile(fmt.Sprintf(`"%s":\[((?:[^\]\\]|\\.)*)\]`, field))
	match := re.FindSubmatch(response)
	if len(match) > 1 {
		inner := string(match[1])
		parts := strings.Split(inner, ",")
		var result []string
		for _, part := range parts {
			cleanedPart := strings.TrimSpace(part)
			if strings.HasPrefix(cleanedPart, "\"") && strings.HasSuffix(cleanedPart, "\"") {
				cleanedPart = cleanedPart[1 : len(cleanedPart)-1]
			}
			unescapedPart, err := unescapeString(cleanedPart)
			if err != nil {
				return nil, fmt.Errorf("unescaping array element: %w", err)
			}
			result = append(result, unescapedPart)
		}
		return result, nil
	}
	return nil, fmt.Errorf("field %s not found", field)
}

func unescapeString(s string) (string, error) {
	var out bytes.Buffer
	for i := 0; i < len(s); i++ {
		if s[i] == '\\' {
			i++
			if i >= len(s) {
				return "", fmt.Errorf("invalid escape sequence")
			}
			switch s[i] {
			case '"', '\\', '/', 'b', 'f', 'n', 'r', 't':
				out.WriteByte('\\')
				out.WriteByte(s[i])
			case 'u':
				return "", fmt.Errorf("unicode escapes not supported")
			default:
				return "", fmt.Errorf("invalid escape sequence")
			}
		} else {
			out.WriteByte(s[i])
		}
	}
	return out.String(), nil
}

func main() {
	flag.StringVar(&docsZipURL, "zip-url", docsUrl, "URL of the documentation zip file")
	flag.Parse()

	log.SetFlags(0) // Remove timestamps from log output

	knowledgeID, err := initKnowledge()
	if err != nil {
		log.Fatalf("Error initializing knowledge: %v", err)
	}
	log.Printf("Collection initialization complete with ID: %s", knowledgeID)

	docsDir, err := os.Getwd()
	if err != nil {
		log.Fatalf("Error getting working directory: %v", err)
	}

	docsContentDir, err := copyMarkdownFiles(docsDir, docsZipURL)
	if err != nil {
		log.Fatalf("Error copying markdown files: %v", err)
	}

	log.Printf("Beginning upload of all markdown files from %s", docsContentDir)

	var markdownFiles []string
	err = filepath.WalkDir(docsContentDir, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !d.IsDir() && (strings.HasSuffix(path, ".md") || strings.HasSuffix(path, ".mdx")) {
			markdownFiles = append(markdownFiles, path)
		}
		return nil
	})

	if err != nil {
		log.Fatalf("Error walking docs content directory: %v", err)
	}

	successfulUploads := 0
	failedUploads := 0
	totalFiles := len(markdownFiles)

	for i, file := range markdownFiles {
		log.Printf("Processing (%d/%d): %s", i+1, totalFiles, file)
		fileID, err := uploadFile(file)
		if err != nil {
			log.Printf("Failed to upload: %s, error: %v", file, err)
			failedUploads++
			continue
		}

		if err := addFileToKnowledge(knowledgeID, fileID); err != nil {
			log.Printf("Failed to add to knowledge base: %s, error: %v", file, err)
			failedUploads++
			continue
		}
		successfulUploads++
		log.Printf("Successfully processed: %s", file)
	}

	log.Println("Upload processing complete.")
	log.Printf("Successfully processed: %d files", successfulUploads)
	log.Printf("Failed to process: %d files", failedUploads)
}
