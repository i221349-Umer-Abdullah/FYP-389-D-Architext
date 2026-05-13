using System;
using System.Drawing;
using System.Windows.Forms;

namespace Architext.Revit
{
    public class GenerateForm : Form
    {
        private TextBox _backendBox;
        private TextBox _promptBox;
        private ComboBox _modeBox;

        public string BackendUrl
        {
            get { return (_backendBox.Text ?? "").Trim().TrimEnd('/'); }
        }

        public string Prompt
        {
            get { return (_promptBox.Text ?? "").Trim(); }
        }

        public string GeneratorMode
        {
            get
            {
                return _modeBox.SelectedIndex == 1 ? "llm" : "gnn";
            }
        }

        public string GeneratorDisplayName
        {
            get
            {
                return GeneratorMode == "gnn" ? "Primary GNN" : "LLM Baseline";
            }
        }

        public GenerateForm()
        {
            Text = "ArchiText Revit Generator";
            Width = 620;
            Height = 430;
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;

            Label title = new Label();
            title.Text = "Generate BIM Floor Plan";
            title.Font = new Font(Font.FontFamily, 14, FontStyle.Bold);
            title.SetBounds(18, 16, 560, 28);
            Controls.Add(title);

            Label backendLabel = new Label();
            backendLabel.Text = "Backend URL";
            backendLabel.SetBounds(20, 58, 120, 22);
            Controls.Add(backendLabel);

            _backendBox = new TextBox();
            _backendBox.Text = "http://localhost:8000";
            _backendBox.SetBounds(150, 56, 420, 24);
            Controls.Add(_backendBox);

            Label modeLabel = new Label();
            modeLabel.Text = "Generator";
            modeLabel.SetBounds(20, 96, 120, 22);
            Controls.Add(modeLabel);

            _modeBox = new ComboBox();
            _modeBox.DropDownStyle = ComboBoxStyle.DropDownList;
            _modeBox.Items.Add("Primary GNN");
            _modeBox.Items.Add("LLM Baseline");
            _modeBox.SelectedIndex = 0;
            _modeBox.SetBounds(150, 94, 220, 24);
            Controls.Add(_modeBox);

            Label promptLabel = new Label();
            promptLabel.Text = "Prompt";
            promptLabel.SetBounds(20, 135, 120, 22);
            Controls.Add(promptLabel);

            _promptBox = new TextBox();
            _promptBox.Multiline = true;
            _promptBox.ScrollBars = ScrollBars.Vertical;
            _promptBox.Text = "A 3 bedroom house with 2 bathrooms, living room, kitchen, dining, parking, and a small garden on a 5 marla plot";
            _promptBox.SetBounds(150, 135, 420, 145);
            Controls.Add(_promptBox);

            Label hint = new Label();
            hint.Text = "Tip: keep the backend running locally before generating.";
            hint.SetBounds(150, 288, 420, 22);
            hint.ForeColor = Color.DimGray;
            Controls.Add(hint);

            Button generate = new Button();
            generate.Text = "Generate and Import";
            generate.SetBounds(310, 330, 150, 34);
            generate.Click += OnGenerate;
            Controls.Add(generate);

            Button cancel = new Button();
            cancel.Text = "Cancel";
            cancel.SetBounds(470, 330, 100, 34);
            cancel.Click += delegate { DialogResult = DialogResult.Cancel; Close(); };
            Controls.Add(cancel);

            AcceptButton = generate;
            CancelButton = cancel;
        }

        private void OnGenerate(object sender, EventArgs e)
        {
            if (BackendUrl.Length == 0)
            {
                MessageBox.Show("Please enter the backend URL.", "ArchiText");
                return;
            }

            if (Prompt.Length == 0)
            {
                MessageBox.Show("Please enter a prompt.", "ArchiText");
                return;
            }

            DialogResult = DialogResult.OK;
            Close();
        }
    }
}

