using System;
using System.IO;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

namespace Architext.Revit
{
    internal class ArchitextClient
    {
        private readonly string _baseUrl;

        public ArchitextClient(string baseUrl)
        {
            _baseUrl = (baseUrl ?? "http://localhost:8000").Trim().TrimEnd('/');
        }

        public string StartGeneration(string prompt, string mode)
        {
            string body = "{\"text\":\"" + EscapeJson(prompt) + "\",\"generator_mode\":\"" + EscapeJson(mode) + "\"}";
            string response = RequestText("POST", "/api/generate", body);
            string jobId = MatchJsonString(response, "job_id");
            if (string.IsNullOrEmpty(jobId))
            {
                throw new InvalidOperationException("Backend did not return a job_id. Response:\n" + response);
            }

            return jobId;
        }

        public void WaitForCompletion(string jobId, int timeoutSeconds)
        {
            DateTime deadline = DateTime.Now.AddSeconds(timeoutSeconds);
            string lastStatus = "";
            string lastMessage = "";

            while (DateTime.Now < deadline)
            {
                Thread.Sleep(1500);
                string response = RequestText("GET", "/api/status/" + Uri.EscapeDataString(jobId), null);
                lastStatus = MatchJsonString(response, "status");
                lastMessage = MatchJsonString(response, "message");

                if (lastStatus == "done")
                {
                    return;
                }

                if (lastStatus == "failed")
                {
                    string error = MatchJsonString(response, "error");
                    throw new InvalidOperationException("Generation failed: " + (string.IsNullOrEmpty(error) ? response : error));
                }
            }

            throw new TimeoutException("Generation timed out. Last status: " + lastStatus + " " + lastMessage);
        }

        public void DownloadIfc(string jobId, string outputPath)
        {
            string url = _baseUrl + "/api/download/" + Uri.EscapeDataString(jobId);
            using (WebClient client = new WebClient())
            {
                client.DownloadFile(url, outputPath);
            }
        }

        private string RequestText(string method, string path, string body)
        {
            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(_baseUrl + path);
            req.Method = method;
            req.Accept = "application/json";

            if (body != null)
            {
                byte[] bytes = Encoding.UTF8.GetBytes(body);
                req.ContentType = "application/json";
                req.ContentLength = bytes.Length;
                using (Stream stream = req.GetRequestStream())
                {
                    stream.Write(bytes, 0, bytes.Length);
                }
            }

            try
            {
                using (HttpWebResponse response = (HttpWebResponse)req.GetResponse())
                using (StreamReader reader = new StreamReader(response.GetResponseStream()))
                {
                    return reader.ReadToEnd();
                }
            }
            catch (WebException ex)
            {
                string error = ex.Message;
                if (ex.Response != null)
                {
                    using (StreamReader reader = new StreamReader(ex.Response.GetResponseStream()))
                    {
                        error += "\n" + reader.ReadToEnd();
                    }
                }
                throw new InvalidOperationException("Backend request failed:\n" + error, ex);
            }
        }

        private static string MatchJsonString(string json, string key)
        {
            Match match = Regex.Match(json, "\"" + Regex.Escape(key) + "\"\\s*:\\s*\"([^\"]*)\"");
            return match.Success ? UnescapeJson(match.Groups[1].Value) : "";
        }

        private static string EscapeJson(string value)
        {
            if (value == null)
            {
                return "";
            }

            return value
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"")
                .Replace("\r", "\\r")
                .Replace("\n", "\\n")
                .Replace("\t", "\\t");
        }

        private static string UnescapeJson(string value)
        {
            if (value == null)
            {
                return "";
            }

            return value
                .Replace("\\n", "\n")
                .Replace("\\r", "\r")
                .Replace("\\t", "\t")
                .Replace("\\\"", "\"")
                .Replace("\\\\", "\\");
        }
    }
}

