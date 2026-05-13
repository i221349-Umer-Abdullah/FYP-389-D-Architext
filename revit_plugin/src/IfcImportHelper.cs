using System;
using System.Diagnostics;
using System.Linq;
using System.Reflection;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace Architext.Revit
{
    internal static class IfcImportHelper
    {
        public static bool ImportOrOpen(UIApplication uiapp, string ifcPath, out string message)
        {
            UIDocument uidoc = uiapp.ActiveUIDocument;
            if (uidoc != null && uidoc.Document != null)
            {
                string importError;
                if (TryImportIntoActiveDocument(uidoc, ifcPath, out importError))
                {
                    message = "Imported into the active Revit document.";
                    return true;
                }
            }

            string openError;
            if (TryOpenIfcDocument(uiapp, ifcPath, out openError))
            {
                message = "Opened IFC as a Revit document.";
                return true;
            }

            Process.Start(new ProcessStartInfo(ifcPath) { UseShellExecute = true });
            message = "Direct Revit import was unavailable, so the IFC was opened with the default system handler.";
            return false;
        }

        private static bool TryImportIntoActiveDocument(UIDocument uidoc, string ifcPath, out string error)
        {
            error = "";

            try
            {
                Document doc = uidoc.Document;
                Type optionsType = FindType("Autodesk.Revit.DB.IFCImportOptions");
                if (optionsType == null)
                {
                    error = "IFCImportOptions type not found.";
                    return false;
                }

                object options = Activator.CreateInstance(optionsType);
                MethodInfo importMethod = doc.GetType()
                    .GetMethods()
                    .FirstOrDefault(m =>
                    {
                        if (m.Name != "Import")
                        {
                            return false;
                        }

                        ParameterInfo[] p = m.GetParameters();
                        return p.Length == 3 &&
                               p[0].ParameterType == typeof(string) &&
                               p[1].ParameterType == optionsType;
                    });

                if (importMethod == null)
                {
                    error = "Document.Import IFC overload not found.";
                    return false;
                }

                using (Transaction tx = new Transaction(doc, "Import ArchiText IFC"))
                {
                    tx.Start();
                    importMethod.Invoke(doc, new object[] { ifcPath, options, uidoc.ActiveView });
                    tx.Commit();
                }

                return true;
            }
            catch (Exception ex)
            {
                error = ex.Message;
                return false;
            }
        }

        private static bool TryOpenIfcDocument(UIApplication uiapp, string ifcPath, out string error)
        {
            error = "";

            try
            {
                object app = uiapp.Application;
                MethodInfo method = app.GetType().GetMethod("OpenIFCDocument", new Type[] { typeof(string) });
                if (method == null)
                {
                    error = "OpenIFCDocument method not found.";
                    return false;
                }

                method.Invoke(app, new object[] { ifcPath });
                return true;
            }
            catch (Exception ex)
            {
                error = ex.Message;
                return false;
            }
        }

        private static Type FindType(string fullName)
        {
            foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type type = assembly.GetType(fullName, false);
                if (type != null)
                {
                    return type;
                }
            }

            return null;
        }
    }
}

